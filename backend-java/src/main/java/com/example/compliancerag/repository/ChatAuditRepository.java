package com.example.compliancerag.repository;

import com.example.compliancerag.entity.ChatAuditLog;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ChatAuditRepository extends JpaRepository<ChatAuditLog, Long> {
}