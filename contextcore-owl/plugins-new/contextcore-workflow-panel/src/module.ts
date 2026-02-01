import { PanelPlugin } from '@grafana/data';
import { WorkflowPanel } from './components/WorkflowPanel';
import { WorkflowPanelOptions } from './types';

export const plugin = new PanelPlugin<WorkflowPanelOptions>(WorkflowPanel).setPanelOptions((builder) => {
  builder
    .addTextInput({
      path: 'apiUrl',
      name: 'Rabbit API URL',
      description: 'Base URL of the Rabbit API server',
      defaultValue: 'http://localhost:8080',
      category: ['Connection'],
    })
    .addTextInput({
      path: 'projectId',
      name: 'Project ID',
      description: 'Project ID or template variable (e.g., $project)',
      defaultValue: '$project',
      category: ['Connection'],
    })
    .addBooleanSwitch({
      path: 'showDryRun',
      name: 'Show Dry Run Button',
      description: 'Display the Dry Run button for previewing workflow execution',
      defaultValue: true,
      category: ['Buttons'],
    })
    .addBooleanSwitch({
      path: 'showExecute',
      name: 'Show Execute Button',
      description: 'Display the Execute button for running workflows',
      defaultValue: true,
      category: ['Buttons'],
    })
    .addBooleanSwitch({
      path: 'confirmExecution',
      name: 'Confirm Execution',
      description: 'Require confirmation before executing workflows',
      defaultValue: true,
      category: ['Buttons'],
    })
    .addNumberInput({
      path: 'refreshInterval',
      name: 'Auto-Refresh Interval',
      description: 'Auto-refresh status interval in seconds (0 to disable)',
      defaultValue: 10,
      category: ['Display'],
    });
});
