package com.example.compliancerag.controller;

import com.example.compliancerag.annotation.SanitizePii; // Don't forget PII!
import com.example.compliancerag.client.PythonAgentClient;
import com.example.compliancerag.service.ChatService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/chat") // Keeping base path
public class ChatController {

    private final ChatService chatService;
    private final PythonAgentClient pythonClient; // <--- New Dependency

    public ChatController(ChatService chatService, PythonAgentClient pythonClient) {
        this.chatService = chatService;
        this.pythonClient = pythonClient;
    }

    // 1. Existing RAG Endpoint (Java Native)
    @GetMapping
    public String chat(@RequestParam String query) {
        return chatService.chat(query);
    }

    // 2. New Agent Endpoint (Delegates to Python)
    @GetMapping("/agent")
    @SanitizePii // <--- Architect Move: Reuse your Security Guardrail!
    public String agentChat(@RequestParam String query) {
        return pythonClient.callAgent(query);
    }
}