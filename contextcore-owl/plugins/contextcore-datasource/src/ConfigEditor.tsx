import React from 'react';
import { DataSourcePluginOptionsEditorProps } from '@grafana/data';
import { Input, InlineField, FieldSet } from '@grafana/ui';
import { ContextCoreDataSourceOptions, ContextCoreSecureJsonData } from './types';

type Props = DataSourcePluginOptionsEditorProps<ContextCoreDataSourceOptions, ContextCoreSecureJsonData>;

export const ConfigEditor: React.FC<Props> = ({ options, onOptionsChange }) => {
  const { jsonData } = options;

  const onUrlChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    onOptionsChange({
      ...options,
      jsonData: {
        ...jsonData,
        url: event.target.value,
      },
    });
  };

  return (
    <FieldSet label="Connection">
      <InlineField
        label="Rabbit API URL"
        labelWidth={14}
        tooltip="The base URL of the Rabbit API server (e.g., http://localhost:8080)"
      >
        <Input
          value={jsonData.url || ''}
          onChange={onUrlChange}
          placeholder="http://localhost:8080"
          width={40}
        />
      </InlineField>
    </FieldSet>
  );
};
