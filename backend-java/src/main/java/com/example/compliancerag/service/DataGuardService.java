package com.example.compliancerag.service;

import org.springframework.stereotype.Service;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

@Service
public class DataGuardService {

    // Regex patterns for common PII
    // (Simple versions for demonstration)
    private static final Pattern EMAIL_PATTERN =
            Pattern.compile("[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,6}");

    private static final Pattern PHONE_PATTERN =
            Pattern.compile("\\b\\d{3}[-.]?\\d{3}[-.]?\\d{4}\\b");

    private static final Pattern SSN_PATTERN =
            Pattern.compile("\\b\\d{3}-\\d{2}-\\d{4}\\b");

    /**
     * Scans the input text and replaces PII with [REDACTED <TYPE>]
     */
    public String sanitize(String input) {
        if (input == null || input.isEmpty()) {
            return input;
        }

        String sanitized = input;

        // 1. Mask Emails
        Matcher emailMatcher = EMAIL_PATTERN.matcher(sanitized);
        sanitized = emailMatcher.replaceAll("[REDACTED EMAIL]");

        // 2. Mask Phone Numbers
        Matcher phoneMatcher = PHONE_PATTERN.matcher(sanitized);
        sanitized = phoneMatcher.replaceAll("[REDACTED PHONE]");

        // 3. Mask SSNs
        Matcher ssnMatcher = SSN_PATTERN.matcher(sanitized);
        sanitized = ssnMatcher.replaceAll("[REDACTED SSN]");

        return sanitized;
    }
}