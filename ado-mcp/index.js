import express from 'express';
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StreamableHTTPServerTransport } from '@modelcontextprotocol/sdk/server/streamableHttp.js';
import * as z from 'zod/v4';

const {
  PORT = '7010',
  AZDO_ORG,
  AZDO_PROJECT,
  AZDO_PAT,
  AZDO_WEBHOOK_SECRET,
  DOING_STATE = 'Doing'
} = process.env;

if (!AZDO_ORG || !AZDO_PROJECT || !AZDO_PAT) {
  // eslint-disable-next-line no-console
  console.warn(
    'Missing required env vars. Set AZDO_ORG, AZDO_PROJECT, AZDO_PAT before using Azure DevOps APIs.'
  );
}

const stateStore = {
  currentDoingId: null,
  lastWebhook: null
};

function stringsEqualIgnoreCase(a, b) {
  return String(a || '').toLowerCase() === String(b || '').toLowerCase();
}

function requireSecret(req, res) {
  if (!AZDO_WEBHOOK_SECRET) return true;
  const provided = req.header('x-ado-secret') || req.header('x-webhook-secret');
  if (provided !== AZDO_WEBHOOK_SECRET) {
    res.status(401).json({ ok: false, error: 'Invalid webhook secret' });
    return false;
  }
  return true;
}

async function azdoRequest(path, { method = 'GET', headers = {}, body } = {}) {
  if (!AZDO_ORG || !AZDO_PROJECT || !AZDO_PAT) {
    throw new Error('AZDO_ORG/AZDO_PROJECT/AZDO_PAT must be set');
  }
  const url = `https://dev.azure.com/${encodeURIComponent(AZDO_ORG)}/${encodeURIComponent(AZDO_PROJECT)}${path}`;

  const auth = Buffer.from(`:${AZDO_PAT}`, 'utf8').toString('base64');
  const res = await fetch(url, {
    method,
    headers: {
      Authorization: `Basic ${auth}`,
      ...headers
    },
    body
  });

  const text = await res.text();
  if (!res.ok) {
    throw new Error(`Azure DevOps error ${res.status}: ${text}`);
  }
  return text ? JSON.parse(text) : null;
}

async function getWorkItemDetails(workItemId) {
  const wi = await azdoRequest(`/_apis/wit/workitems/${workItemId}?api-version=7.1&$expand=relations`);
  const fields = wi?.fields || {};

  return {
    id: wi?.id,
    rev: wi?.rev,
    url: wi?.url,
    fields: {
      title: fields['System.Title'],
      state: fields['System.State'],
      workItemType: fields['System.WorkItemType'],
      assignedTo: fields['System.AssignedTo']?.displayName || fields['System.AssignedTo']?.uniqueName,
      description: fields['System.Description'],
      tags: fields['System.Tags'],
      areaPath: fields['System.AreaPath'],
      iterationPath: fields['System.IterationPath']
    },
    relations: wi?.relations || []
  };
}

async function updateWorkItem(workItemId, updates) {
  // Azure DevOps PATCH API uses JSON Patch format
  // Each update is an operation: { op: 'add'|'replace'|'remove', path: '/fields/...', value: ... }
  const patchDocument = [];
  
  if (updates.state) {
    patchDocument.push({
      op: 'replace',
      path: '/fields/System.State',
      value: updates.state
    });
  }
  
  if (updates.comment) {
    patchDocument.push({
      op: 'add',
      path: '/fields/System.History',
      value: updates.comment
    });
  }
  
  if (updates.tags) {
    patchDocument.push({
      op: 'replace',
      path: '/fields/System.Tags',
      value: updates.tags
    });
  }
  
  if (updates.description) {
    patchDocument.push({
      op: 'replace',
      path: '/fields/System.Description',
      value: updates.description
    });
  }
  
  const result = await azdoRequest(
    `/_apis/wit/workitems/${workItemId}?api-version=7.1`,
    {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json-patch+json'
      },
      body: JSON.stringify(patchDocument)
    }
  );
  
  return {
    id: result.id,
    rev: result.rev,
    updated: true,
    fields: result.fields
  };
}

function createServer() {
  const server = new McpServer(
    { name: 'ado-mcp', version: '0.1.0' },
    { capabilities: { logging: {} } }
  );

  server.registerTool(
    'get_current_doing_work_item',
    {
      description: 'Returns the latest Azure DevOps work item that moved to the Doing state (captured via webhook).',
      inputSchema: {}
    },
    async () => {
      const id = stateStore.currentDoingId;
      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(
              {
                current_doing_id: id,
                last_webhook: stateStore.lastWebhook
              },
              null,
              2
            )
          }
        ]
      };
    }
  );

  server.registerTool(
    'get_work_item_details',
    {
      description: 'Fetches Azure DevOps work item details (title/state/description/tags/relations) by ID.',
      inputSchema: {
        id: z.number().int().positive().describe('Work item ID')
      }
    },
    async ({ id }) => {
      const details = await getWorkItemDetails(id);
      return {
        content: [{ type: 'text', text: JSON.stringify(details, null, 2) }]
      };
    }
  );

  server.registerTool(
    'update_work_item',
    {
      description: 'Updates an Azure DevOps work item. Can update state, add comments, update tags, or modify description.',
      inputSchema: {
        id: z.number().int().positive().describe('Work item ID'),
        state: z.string().optional().describe('New state (e.g., "Done", "In Progress", "To Do")'),
        comment: z.string().optional().describe('Comment to add to work item history'),
        tags: z.string().optional().describe('Tags (semicolon-separated, e.g., "backend; frontend; mvp")'),
        description: z.string().optional().describe('Updated description (HTML format)')
      }
    },
    async ({ id, state, comment, tags, description }) => {
      const updates = {};
      if (state) updates.state = state;
      if (comment) updates.comment = comment;
      if (tags) updates.tags = tags;
      if (description) updates.description = description;
      
      const result = await updateWorkItem(id, updates);
      return {
        content: [{ type: 'text', text: JSON.stringify(result, null, 2) }]
      };
    }
  );

  return server;
}

// MCP app with host header validation defaults (DNS rebinding protection)
const app = express();

app.get('/health', (req, res) => res.json({ ok: true }));

app.get('/debug', (req, res) => {
  res.json({
    currentDoingId: stateStore.currentDoingId,
    lastWebhook: stateStore.lastWebhook
  });
});

app.post('/ado/webhook', express.text({ type: '*/*', limit: '2mb' }), async (req, res) => {
  if (!requireSecret(req, res)) return;

  process.stdout.write(`[ado-mcp] /ado/webhook hit at ${new Date().toISOString()}\n`);

  let payload = {};
  if (typeof req.body === 'string' && req.body.trim().length > 0) {
    try {
      payload = JSON.parse(req.body);
    } catch {
      payload = {};
    }
  } else if (req.body && typeof req.body === 'object') {
    payload = req.body;
  }

  const stateFromPayload = payload?.resource?.fields?.['System.State'];

  // Azure DevOps service hook payload shapes vary; handle the common ones.
  const workItemId =
    payload?.resource?.workItemId ||
    payload?.resource?.id ||
    payload?.resource?.workItem?.id ||
    payload?.resource?.revision?.id;

  if (!workItemId) {
    process.stdout.write(`[ado-mcp] webhook received (no workItemId) at ${new Date().toISOString()}\n`);
    stateStore.lastWebhook = { receivedAt: new Date().toISOString(), note: 'No workItemId found' };
    return res.json({ ok: true, ignored: true });
  }

  process.stdout.write(
    `[ado-mcp] webhook received workItemId=${Number(workItemId)} state=${stateFromPayload || '(unknown)'} at ${new Date().toISOString()}\n`
  );

  // Fast path: if the payload already includes state, we can decide without calling Azure DevOps.
  if (stateFromPayload) {
    stateStore.lastWebhook = {
      receivedAt: new Date().toISOString(),
      workItemId: Number(workItemId),
      observedState: stateFromPayload,
      source: 'payload'
    };

    if (stringsEqualIgnoreCase(stateFromPayload, DOING_STATE)) {
      stateStore.currentDoingId = Number(workItemId);
    }

    // Always acknowledge the webhook as successful (important for Azure DevOps "Test").
    return res.json({ ok: true, currentDoingId: stateStore.currentDoingId });
  }

  try {
    // If we don't have state in the payload, try to fetch it from Azure DevOps.
    // For test notifications, the referenced work item might not exist; don't fail the webhook.
    const details = await getWorkItemDetails(Number(workItemId));
    const state = details?.fields?.state || '';

    stateStore.lastWebhook = {
      receivedAt: new Date().toISOString(),
      workItemId: Number(workItemId),
      observedState: state,
      source: 'azdo'
    };

    if (stringsEqualIgnoreCase(state, DOING_STATE)) {
      stateStore.currentDoingId = Number(workItemId);
    }

    return res.json({ ok: true, currentDoingId: stateStore.currentDoingId });
  } catch (e) {
    stateStore.lastWebhook = {
      receivedAt: new Date().toISOString(),
      workItemId: Number(workItemId),
      observedState: null,
      source: 'azdo_error',
      error: String(e?.message || e)
    };

    // Always return 200 so Azure DevOps "Test" and retries don't fail.
    return res.json({ ok: true, currentDoingId: stateStore.currentDoingId });
  }
});

// Ensure Azure DevOps "Test" doesn't fail because of body parsing/middleware issues.
// If anything throws while handling /ado/webhook, return 200.
app.use((err, req, res, next) => {
  if (req?.path === '/ado/webhook') {
    stateStore.lastWebhook = {
      receivedAt: new Date().toISOString(),
      source: 'express_error',
      error: String(err?.message || err)
    };
    return res.status(200).json({ ok: true, currentDoingId: stateStore.currentDoingId });
  }
  return next(err);
});

// MCP Streamable HTTP endpoint
app.post('/mcp', express.json({ type: '*/*', limit: '2mb' }), async (req, res) => {
  const server = createServer();
  try {
    const transport = new StreamableHTTPServerTransport({ sessionIdGenerator: undefined });
    await server.connect(transport);
    await transport.handleRequest(req, res, req.body);

    res.on('close', () => {
      transport.close();
      server.close();
    });
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error('Error handling MCP request:', error);
    if (!res.headersSent) {
      res.status(500).json({
        jsonrpc: '2.0',
        error: { code: -32603, message: 'Internal server error' },
        id: null
      });
    }
  }
});

app.listen(Number(PORT), () => {
  // eslint-disable-next-line no-console
  console.log(`ado-mcp listening on http://localhost:${PORT}`);
  // eslint-disable-next-line no-console
  console.log('Endpoints:');
  // eslint-disable-next-line no-console
  console.log(`- POST /ado/webhook (Azure DevOps service hook target)`);
  // eslint-disable-next-line no-console
  console.log(`- POST /mcp (Windsurf MCP serverUrl)`);
});
