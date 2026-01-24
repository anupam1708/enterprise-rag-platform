package com.example.compliancerag.client;

import com.example.compliancerag.dto.AgentRequest;
import com.example.compliancerag.dto.AgentResponse;
import io.github.resilience4j.circuitbreaker.annotation.CircuitBreaker;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;

@Service
public class PythonAgentClient {

    private static final Logger log = LoggerFactory.getLogger(PythonAgentClient.class);
    private final RestClient restClient;
    private final String pythonUrl;

    public PythonAgentClient(RestClient.Builder builder, @Value("${python.agent.url}") String pythonUrl) {
        this.restClient = builder.build();
        this.pythonUrl = pythonUrl;
    }

    @CircuitBreaker(name = "pythonAgent", fallbackMethod = "fallbackCallAgent") // <--- The Guard
    public String callAgent(String query) {
        log.info("🚀 Forwarding request to Python Agent: {}", query);

        AgentRequest request = new AgentRequest(query);
        AgentResponse response = restClient.post()
                .uri(pythonUrl)
                .body(request)
                .retrieve()
                .body(AgentResponse.class);

        return response != null ? response.answer() : "Error: No response";
    }

    // The Fallback (Must have same signature + Throwable)
    public String fallbackCallAgent(String query, Throwable t) {
        log.warn("⚠️ Python Agent is down! Reason: {}. Switching to Fallback.", t.getMessage());
        return "⚠️ The Advanced Agent is currently offline. " +
                "Please try asking standard compliance questions (Local RAG) instead.";
    }
}