package com.example.compliancerag.service;

import com.example.compliancerag.annotation.SanitizePii;
import com.example.compliancerag.client.PythonAgentClient;
import com.example.compliancerag.entity.ChatAuditLog;
import com.example.compliancerag.repository.ChatAuditRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.ai.chat.client.ChatClient;
import org.springframework.ai.document.Document;
import org.springframework.ai.vectorstore.SearchRequest;
import org.springframework.ai.vectorstore.VectorStore;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.stream.Collectors;

@Service
public class ChatService {

    private static final Logger log = LoggerFactory.getLogger(ChatService.class);

    private final VectorStore vectorStore;
    private final ChatClient chatClient;
    private final ChatAuditRepository auditRepository;
    private final PythonAgentClient pythonAgentClient;

    public ChatService(VectorStore vectorStore, ChatClient.Builder chatClientBuilder, 
                      ChatAuditRepository auditRepository, PythonAgentClient pythonAgentClient) {
        this.vectorStore = vectorStore;
        this.chatClient = chatClientBuilder.build();
        this.auditRepository = auditRepository;
        this.pythonAgentClient = pythonAgentClient;
    }

    @SanitizePii
    public String chat(String query) {
        // 1. Retrieve the most similar documents (The "Search" part)
        // We ask for the top 3 matches
        List<Document> similarDocuments = vectorStore.similaritySearch(
                SearchRequest.builder().query(query).topK(3).build()
        );

        String aiResponse;

        // 2. Check if we have relevant documents
        if (similarDocuments.isEmpty()) {
            // No documents found - use Python agent with search tools
            log.info("📚 No documents in vector store. Routing to Python Agent with search tools.");
            aiResponse = pythonAgentClient.callAgent(query);
        } else {
            // Documents found - use traditional RAG
            log.info("📚 Found {} documents. Using RAG approach.", similarDocuments.size());
            
            // Combine the found documents into a single "Context" string
            String context = similarDocuments.stream()
                    .map(Document::getText)
                    .collect(Collectors.joining("\n"));

            // Construct the "Prompt" (The "Generation" part)
            String systemPrompt = """
                    You are a helpful AI assistant.
                    Answer the user's question using ONLY the following context.
                    If the answer is not in the context, say "I don't know based on the documents provided."
                    
                    CONTEXT:
                    """ + context;

            // Call the LLM
            aiResponse = chatClient.prompt()
                    .system(systemPrompt)
                    .user(query)
                    .call()
                    .content();
        }

        // 3. ARCHITECT STEP: Audit Logging
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