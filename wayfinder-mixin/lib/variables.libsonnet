// Template variable builders for Wayfinder dashboards.
{
  // Prometheus/Mimir datasource variable
  prometheusDatasource(name='datasource', label='Datasource'):: {
    name: name,
    label: label,
    type: 'datasource',
    query: 'prometheus',
    current: { text: 'Mimir', value: 'mimir' },
    refresh: 1,
  },

  // Tempo datasource variable
  tempoDatasource(name='tempo', label='Tempo'):: {
    name: name,
    label: label,
    type: 'datasource',
    query: 'tempo',
    current: { text: 'Tempo', value: 'tempo' },
    refresh: 1,
  },

  // Loki datasource variable
  lokiDatasource(name='loki', label='Loki'):: {
    name: name,
    label: label,
    type: 'datasource',
    query: 'loki',
    current: { text: 'Loki', value: 'loki' },
    refresh: 1,
  },

  // Project variable from metric labels
  projectVariable(metric, name='project', label='Project'):: {
    name: name,
    label: label,
    type: 'query',
    datasource: { type: 'prometheus', uid: '${datasource}' },
    query: 'label_values(%s, project_id)' % metric,
    refresh: 1,
    includeAll: true,
    allValue: '.*',
    current: { text: 'All', value: '$__all' },
  },
}
