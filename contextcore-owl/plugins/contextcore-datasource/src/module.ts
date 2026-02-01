import { DataSourcePlugin } from '@grafana/data';
import { DataSource } from './datasource';
import { ConfigEditor } from './ConfigEditor';
import { QueryEditor } from './QueryEditor';
import { ContextCoreQuery, ContextCoreDataSourceOptions } from './types';

export const plugin = new DataSourcePlugin<DataSource, ContextCoreQuery, ContextCoreDataSourceOptions>(DataSource)
  .setConfigEditor(ConfigEditor)
  .setQueryEditor(QueryEditor);
