import React from 'react';
import { QueryEditorProps } from '@grafana/data';
import { TextArea, InlineField, InlineFieldRow } from '@grafana/ui';
import { DataSource } from '../datasource';
import { ContextCoreDataSourceOptions, ContextCoreQuery, DEFAULT_QUERY } from '../types';

type Props = QueryEditorProps<DataSource, ContextCoreQuery, ContextCoreDataSourceOptions>;

export const QueryEditor: React.FC<Props> = ({ query, onChange, onRunQuery }) => {
  const onQueryTextChange = (event: React.ChangeEvent<HTMLTextAreaElement>) => {
    onChange({ ...query, queryText: event.target.value });
  };

  const onBlur = () => {
    if (query.queryText?.trim()) {
      onRunQuery();
    }
  };

  const { queryText } = { ...DEFAULT_QUERY, ...query };

  return (
    <InlineFieldRow>
      <InlineField label="Prompt" labelWidth={10} grow>
        <TextArea
          value={queryText}
          onChange={onQueryTextChange}
          onBlur={onBlur}
          placeholder="Enter your prompt for Claude..."
          rows={4}
        />
      </InlineField>
    </InlineFieldRow>
  );
};
