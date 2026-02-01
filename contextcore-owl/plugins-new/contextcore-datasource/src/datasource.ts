import {
  DataSourceInstanceSettings,
  DataQueryRequest,
  DataQueryResponse,
  DataSourceApi,
  MutableDataFrame,
  FieldType,
} from '@grafana/data';
import { getBackendSrv } from '@grafana/runtime';
import { ContextCoreDataSourceOptions, ContextCoreQuery, WebhookResponse } from './types';

export class DataSource extends DataSourceApi<ContextCoreQuery, ContextCoreDataSourceOptions> {
  baseUrl: string;

  constructor(instanceSettings: DataSourceInstanceSettings<ContextCoreDataSourceOptions>) {
    super(instanceSettings);
    this.baseUrl = instanceSettings.jsonData.url || 'http://localhost:8080';
  }

  async query(options: DataQueryRequest<ContextCoreQuery>): Promise<DataQueryResponse> {
    const promises = options.targets
      .filter((target) => !target.hide && target.queryText?.trim())
      .map(async (target) => {
        const startTime = Date.now();

        try {
          const response = await getBackendSrv().fetch<WebhookResponse>({
            url: `${this.baseUrl}/invoke`,
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            data: { prompt: target.queryText },
          }).toPromise();

          const data = response?.data;
          const endTime = Date.now();

          if (data?.success) {
            return new MutableDataFrame({
              refId: target.refId,
              fields: [
                { name: 'Time', type: FieldType.time, values: [endTime] },
                { name: 'Prompt', type: FieldType.string, values: [target.queryText] },
                { name: 'Response', type: FieldType.string, values: [data.response] },
                { name: 'Tokens', type: FieldType.number, values: [data.metrics?.total_tokens || 0] },
                { name: 'Response Time (ms)', type: FieldType.number, values: [data.metrics?.response_time_ms || (endTime - startTime)] },
                { name: 'Model', type: FieldType.string, values: [data.model || 'unknown'] },
              ],
            });
          } else {
            return new MutableDataFrame({
              refId: target.refId,
              fields: [
                { name: 'Time', type: FieldType.time, values: [endTime] },
                { name: 'Error', type: FieldType.string, values: [data?.error || 'Unknown error'] },
              ],
            });
          }
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Request failed';
          return new MutableDataFrame({
            refId: target.refId,
            fields: [
              { name: 'Time', type: FieldType.time, values: [Date.now()] },
              { name: 'Error', type: FieldType.string, values: [errorMessage] },
            ],
          });
        }
      });

    return { data: await Promise.all(promises) };
  }

  async testDatasource(): Promise<{ status: string; message: string }> {
    try {
      const response = await getBackendSrv().fetch({
        url: `${this.baseUrl}/health`,
        method: 'GET',
      }).toPromise();

      if (response?.status === 200) {
        return {
          status: 'success',
          message: 'Connection successful! Rabbit API server is running.',
        };
      }
      return {
        status: 'error',
        message: `Unexpected response: HTTP ${response?.status}`,
      };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Connection failed';
      return {
        status: 'error',
        message: `Cannot connect to Rabbit API: ${errorMessage}`,
      };
    }
  }
}
