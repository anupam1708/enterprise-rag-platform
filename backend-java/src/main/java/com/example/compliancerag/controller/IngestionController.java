package com.example.compliancerag.controller;

import com.example.compliancerag.service.IngestionService;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

@RestController
@RequestMapping("/api/ingest")
public class IngestionController {

    private final IngestionService ingestionService;

    public IngestionController(IngestionService ingestionService) {
        this.ingestionService = ingestionService;
    }

    @PostMapping
    public String ingestPdf(@RequestParam("file") MultipartFile file) {
        if (file.isEmpty()) {
            return "Error: File is empty";
        }

        // Convert MultipartFile to Spring Resource and pass to service
        ingestionService.ingest(file.getResource());

        return "Success: Ingested " + file.getOriginalFilename();
    }
}