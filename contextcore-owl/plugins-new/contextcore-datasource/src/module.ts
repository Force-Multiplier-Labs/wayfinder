import { DataSourcePlugin } from '@grafana/data';
import { DataSource } from './datasource';
import { ConfigEditor } from './components/ConfigEditor';
import { QueryEditor } from './components/QueryEditor';
import { ContextCoreQuery, ContextCoreDataSourceOptions } from './types';

export const plugin = new DataSourcePlugin<DataSource, ContextCoreQuery, ContextCoreDataSourceOptions>(DataSource)
  .setConfigEditor(ConfigEditor)
  .setQueryEditor(QueryEditor);
