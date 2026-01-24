package com.example.compliancerag.aspect;

import com.example.compliancerag.service.DataGuardService;
import org.aspectj.lang.ProceedingJoinPoint;
import org.aspectj.lang.annotation.Around;
import org.aspectj.lang.annotation.Aspect;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.util.Arrays;

@Aspect
@Component
public class PiiSanitizationAspect {

    private static final Logger log = LoggerFactory.getLogger(PiiSanitizationAspect.class);
    private final DataGuardService dataGuardService;

    public PiiSanitizationAspect(DataGuardService dataGuardService) {
        this.dataGuardService = dataGuardService;
    }

    @Around("@annotation(com.example.compliancerag.annotation.SanitizePii)")
    public Object sanitizeArguments(ProceedingJoinPoint joinPoint) throws Throwable {
        Object[] args = joinPoint.getArgs();
        boolean modified = false;

        // Iterate through all arguments
        for (int i = 0; i < args.length; i++) {
            if (args[i] instanceof String) {
                String original = (String) args[i];
                String sanitized = dataGuardService.sanitize(original);

                // If sanitization changed the string, update the argument array
                if (!original.equals(sanitized)) {
                    log.warn("🛡️ AOP Guardrail: PII detected in argument [{}]. Redacting...", i);
                    args[i] = sanitized;
                    modified = true;
                }
            }
        }

        // Proceed with the (possibly modified) arguments
        return joinPoint.proceed(args);
    }
}