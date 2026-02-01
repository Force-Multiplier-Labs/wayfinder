import { PanelPlugin } from '@grafana/data';
import { ChatPanel } from './components/ChatPanel';
import { ChatPanelOptions } from './types';

export const plugin = new PanelPlugin<ChatPanelOptions>(ChatPanel).setPanelOptions((builder) => {
  builder
    .addTextInput({
      path: 'webhookUrl',
      name: 'Webhook URL',
      description: 'URL of the webhook server to send prompts to',
      defaultValue: 'http://localhost:8080/invoke',
      category: ['Connection'],
    })
    .addBooleanSwitch({
      path: 'showMetrics',
      name: 'Show Metrics',
      description: 'Display response metrics (tokens, response time)',
      defaultValue: true,
      category: ['Display'],
    })
    .addNumberInput({
      path: 'maxHeight',
      name: 'Max Response Height',
      description: 'Maximum height for response area in pixels (0 for auto)',
      defaultValue: 300,
      category: ['Display'],
    })
    .addTextInput({
      path: 'placeholder',
      name: 'Placeholder Text',
      description: 'Placeholder text shown in the input area',
      defaultValue: 'Ask a question about your metrics...',
      category: ['Display'],
    });
});
