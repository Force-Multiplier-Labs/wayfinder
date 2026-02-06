// Notification policy factory: Takes service params, produces Grafana notification policy YAML.
local defaults = import './service_config.libsonnet';

// Factory function: takes service params, returns notification policy object
function(params)
  local s = defaults + params;

  // Determine receivers based on criticality
  local criticalReceiver = if s.criticality == 'critical' then 'pagerduty-p1'
    else if s.criticality == 'high' then 'slack-incidents'
    else 'email-oncall';

  local warningReceiver = if s.criticality == 'critical' then 'slack-incidents'
    else if s.criticality == 'high' then 'slack-incidents'
    else 'slack-notifications';

  // Repeat intervals based on criticality
  local criticalRepeat = if s.criticality == 'critical' then '5m'
    else if s.criticality == 'high' then '15m'
    else '1h';

  local warningRepeat = if s.criticality == 'critical' then '30m'
    else if s.criticality == 'high' then '1h'
    else '4h';

  // Build contact points from alertChannels if provided
  local contactPoints = if std.length(s.alertChannels) > 0 then [
    {
      name: channel,
      type: if std.startsWith(channel, 'pagerduty') then 'pagerduty'
        else if std.startsWith(channel, 'slack') then 'slack'
        else if std.startsWith(channel, 'email') then 'email'
        else 'webhook',
      [if std.startsWith(channel, 'slack') then 'settings']: {
        channel: 'online-boutique-alerts',
      },
    }
    for channel in s.alertChannels
  ] else [
    {
      name: 'pagerduty-p1',
      type: 'pagerduty',
    },
    {
      name: 'slack-incidents',
      type: 'slack',
      settings: {
        channel: 'online-boutique-alerts',
      },
    },
    {
      name: 'email-oncall',
      type: 'email',
      settings: {
        addresses: '%s-oncall@example.com' % s.owner,
      },
    },
  ];

  // Build the notification policy resource
  {
    apiVersion: 'alerting.grafana.com/v1',
    kind: 'NotificationPolicy',
    metadata: {
      name: '%s-notifications' % s.name,
      namespace: 'online-boutique',
      labels: {
        app: s.name,
        tier: s.criticality,
      },
    },
    spec: {
      service: s.name,
      criticality: s.criticality,
      owner: s.owner,
      routes: [
        // Critical severity route
        {
          matchers: [
            { name: 'service', value: s.name },
            { name: 'severity', value: 'critical' },
          ],
          receiver: criticalReceiver,
          repeatInterval: criticalRepeat,
          continueMatching: false,
        },
        // Warning severity route
        {
          matchers: [
            { name: 'service', value: s.name },
            { name: 'severity', value: 'warning' },
          ],
          receiver: warningReceiver,
          repeatInterval: warningRepeat,
          continueMatching: false,
        },
        // Info severity route
        {
          matchers: [
            { name: 'service', value: s.name },
            { name: 'severity', value: 'info' },
          ],
          receiver: 'slack-notifications',
          repeatInterval: '4h',
          continueMatching: false,
        },
      ],
      contactPoints: contactPoints,
      // Mute timings for maintenance windows
      muteTimings: [
        {
          name: 'maintenance-window',
          timeIntervals: [
            {
              weekdays: ['monday:friday'],
              times: [{ startTime: '02:00', endTime: '04:00' }],
              location: 'UTC',
            },
          ],
        },
      ],
      // Escalation policy
      escalation: {
        enabled: true,
        waitMinutes: 15,
        escalateTo: if s.criticality == 'critical' then 'pagerduty-p1'
          else 'slack-incidents',
      },
    },
  }
