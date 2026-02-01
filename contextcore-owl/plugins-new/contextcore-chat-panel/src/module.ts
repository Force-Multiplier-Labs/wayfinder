import { PanelPlugin } from '@grafana/data';
import { ChatPanelOptions } from './types';
import { ChatPanel } from './components/ChatPanel';

export const plugin = new PanelPlugin<ChatPanelOptions>(ChatPanel).setPanelOptions((builder) => {
  return builder
    .addTextInput({
      path: 'webhookUrl',
      name: 'Webhook URL',
      description: 'URL of the Claude webhook server',
      defaultValue: 'http://localhost:8080/invoke',
    })
    .addNumberInput({
      path: 'maxHeight',
      name: 'Max Response Height',
      description: 'Maximum height for response area in pixels (0 for auto)',
      defaultValue: 400,
    })
    .addBooleanSwitch({
      path: 'showMetrics',
      name: 'Show Metrics',
      description: 'Display response metrics (tokens, time)',
      defaultValue: true,
    })
    .addTextInput({
      path: 'placeholder',
      name: 'Placeholder Text',
      description: 'Placeholder text for the input area',
      defaultValue: 'Ask Claude a question...',
    });
});
