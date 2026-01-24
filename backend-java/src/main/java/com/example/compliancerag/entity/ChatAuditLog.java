package com.example.compliancerag.entity;

import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "chat_audit_logs")
public class ChatAuditLog {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private String userQuery;

    @Column(nullable = false)
    private String sanitizedQuery;

    @Column(length = 5000) // Allow long AI responses
    private String aiResponse;

    private LocalDateTime timestamp;

    private boolean piiDetected;

    // Constructors
    public ChatAuditLog() {}

    public ChatAuditLog(String userQuery, String sanitizedQuery, String aiResponse, boolean piiDetected) {
        this.userQuery = userQuery;
        this.sanitizedQuery = sanitizedQuery;
        this.aiResponse = aiResponse;
        this.piiDetected = piiDetected;
        this.timestamp = LocalDateTime.now();
    }

    // Getters (Lombok @Data would be cleaner, but keeping it standard Java)
    public Long getId() { return id; }
    public String getUserQuery() { return userQuery; }
    public String getSanitizedQuery() { return sanitizedQuery; }
    public String getAiResponse() { return aiResponse; }
    public LocalDateTime getTimestamp() { return timestamp; }
    public boolean isPiiDetected() { return piiDetected; }
}