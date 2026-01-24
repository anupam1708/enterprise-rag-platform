package com.example.compliancerag.service;

import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.text.PDFTextStripper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.ai.document.Document;
import org.springframework.ai.transformer.splitter.TokenTextSplitter;
import org.springframework.ai.vectorstore.VectorStore;
import org.springframework.core.io.Resource;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

@Service
public class IngestionService {

    private static final Logger log = LoggerFactory.getLogger(IngestionService.class);
    private final VectorStore vectorStore;

    public IngestionService(VectorStore vectorStore) {
        this.vectorStore = vectorStore;
    }

    public void ingest(Resource pdfResource) {
        try {
            // 1. Extract Text from PDF (Using Apache PDFBox)
            // Ideally, you'd use Spring AI's PagePdfDocumentReader, but this shows you how it works under the hood.
            PDDocument document = PDDocument.load(pdfResource.getInputStream());
            PDFTextStripper stripper = new PDFTextStripper();
            String fullText = stripper.getText(document);
            document.close();

            log.info("Extracted {} characters from PDF", fullText.length());

            // 2. Split into Chunks (The "Art" of RAG)
            // We split by tokens (roughly words), not just characters, to keep context intact.
            // 800 tokens is about 1/2 page of text.
            TokenTextSplitter splitter = new TokenTextSplitter(800, 400, 5, 10000, true);
            
            // Create a document from the full text
            Document sourceDoc = new Document(fullText);
            
            // Split the document into chunks
            List<Document> documents = splitter.split(sourceDoc);

            // 4. Store in Vector DB (This calls OpenAI to get embeddings + saves to Postgres)
            vectorStore.add(documents);
            log.info("Successfully ingested {} chunks into pgvector!", documents.size());

        } catch (IOException e) {
            log.error("Failed to parse PDF", e);
            throw new RuntimeException(e);
        }
    }
}
