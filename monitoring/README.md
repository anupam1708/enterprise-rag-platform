# Monitoring & Observability

This platform includes comprehensive monitoring using Prometheus and Grafana.

## Services

### Prometheus (Port 9090)
- **URL**: http://localhost:9090
- **Purpose**: Metrics collection and alerting
- Scrapes metrics from Spring Boot Actuator every 15 seconds
- Evaluates alert rules for service health

### Grafana (Port 3001)
- **URL**: http://localhost:3001
- **Login**: admin / admin
- **Purpose**: Metrics visualization
- Pre-configured with Spring Boot dashboard

## Metrics Available

### Application Metrics
- **Request Rate**: Requests per second per endpoint
- **Response Time**: P50 and P95 latency percentiles
- **Error Rate**: 4xx and 5xx error counts
- **Active Requests**: Concurrent request count

### JVM Metrics
- **Memory Usage**: Heap and non-heap memory
- **GC Activity**: Garbage collection pause time
- **Thread Count**: Active threads
- **CPU Usage**: Process CPU utilization

### Database Metrics
- **Connection Pool**: Active, idle, and max connections
- **Query Performance**: Hikari CP metrics
- **Connection Wait Time**: Time waiting for connections

## Alerts Configured

### Critical Alerts
1. **ServiceDown**: Service unreachable for >1 minute
2. **DatabaseConnectionPoolExhausted**: All DB connections in use

### Warning Alerts
1. **HighErrorRate**: >5% error rate for 5 minutes
2. **HighMemoryUsage**: >90% JVM memory usage for 5 minutes
3. **SlowAPIResponse**: P95 latency >2 seconds for 5 minutes

## Accessing Monitoring

### View Prometheus Metrics
```bash
# Raw metrics endpoint
curl http://localhost:8080/actuator/prometheus

# Prometheus UI
open http://localhost:9090
```

### View Grafana Dashboard
```bash
# Open Grafana
open http://localhost:3001

# Login with:
# Username: admin
# Password: admin
```

### Query Examples in Prometheus

```promql
# Request rate per endpoint
rate(http_server_requests_seconds_count[5m])

# Memory usage percentage
(jvm_memory_used_bytes / jvm_memory_max_bytes) * 100

# Database connections
hikaricp_connections_active

# Error rate
rate(http_server_requests_seconds_count{status=~"5.."}[5m])
```

## Dashboard Panels

The pre-configured Grafana dashboard includes:
1. **Service Status**: Real-time service health
2. **Request Rate**: Traffic patterns over time
3. **Response Time**: Latency percentiles (P50, P95)
4. **JVM Memory**: Heap usage trends
5. **Database Pool**: Connection pool utilization

## Alert Notifications

To enable alert notifications (email, Slack, PagerDuty):

1. Add Alertmanager to docker-compose.yml
2. Configure alert routing in `monitoring/alertmanager.yml`
3. Update Prometheus config to use Alertmanager

## Custom Metrics

Add custom business metrics in your code:

```java
@Component
public class CustomMetrics {
    private final Counter documentsIngested;
    private final Timer chatResponseTime;
    
    public CustomMetrics(MeterRegistry registry) {
        documentsIngested = Counter.builder("documents.ingested.total")
            .description("Total documents ingested")
            .register(registry);
            
        chatResponseTime = Timer.builder("chat.response.time")
            .description("AI chat response time")
            .register(registry);
    }
}
```

## Troubleshooting

### Prometheus not scraping metrics
```bash
# Check if actuator is exposed
curl http://localhost:8080/actuator/prometheus

# Check Prometheus targets
open http://localhost:9090/targets
```

### Grafana dashboard empty
1. Verify Prometheus datasource is connected
2. Check time range in dashboard (default: last 6 hours)
3. Generate some traffic to the application

### High memory alerts
```bash
# Check JVM heap settings in Dockerfile
ENV JAVA_OPTS="-Xmx512m -Xms256m"
```
