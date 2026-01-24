package com.example.compliancerag.service;

import com.example.compliancerag.annotation.SanitizePii;
import com.example.compliancerag.entity.ChatAuditLog;
import com.example.compliancerag.repository.ChatAuditRepository;
import org.springframework.ai.chat.client.ChatClient;
import org.springframework.ai.document.Document;
import org.springframework.ai.vectorstore.SearchRequest;
import org.springframework.ai.vectorstore.VectorStore;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.stream.Collectors;

@Service
public class ChatService {

    private final VectorStore vectorStore;
    private final ChatClient chatClient;
    private final ChatAuditRepository auditRepository;

    public ChatService(VectorStore vectorStore, ChatClient.Builder chatClientBuilder, ChatAuditRepository auditRepository) {
        this.vectorStore = vectorStore;
        this.chatClient = chatClientBuilder.build();
        this.auditRepository = auditRepository;
    }

    @SanitizePii
    public String chat(String query) {
        // 1. Retrieve the most similar documents (The "Search" part)
        // We ask for the top 3 matches
        List<Document> similarDocuments = vectorStore.similaritySearch(
                SearchRequest.builder().query(query).topK(3).build()
        );

        // 2. Combine the found documents into a single "Context" string
        String context = similarDocuments.stream()
                .map(Document::getText)
                .collect(Collectors.joining("\n"));

        // 3. Construct the "Prompt" (The "Generation" part)
        // We tell the LLM: "Only use this context to answer."
        String systemPrompt = """
                You are a helpful AI assistant.
                Answer the user's question using ONLY the following context.
                If the answer is not in the context, say "I don't know based on the documents provided."
                
                CONTEXT:
                """ + context;

        // 4. Call the LLM
        String aiResponse = chatClient.prompt()
                .system(systemPrompt)
                .user(query)
                .call()
                .content();

        // 5. ARCHITECT STEP: Audit Logging
        // We log what actually happened.
        ChatAuditLog log = new ChatAuditLog(
                query,      // Storing sanitized query as "User Query"
                query,      // Storing sanitized query
                aiResponse,
                false       // We assume false here since AOP handled the check invisibly
        );
        auditRepository.save(log);

        return aiResponse;
    }
}