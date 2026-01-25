package com.example.compliancerag.service;

import com.example.compliancerag.dto.AuthResponse;
import com.example.compliancerag.dto.LoginRequest;
import com.example.compliancerag.dto.RegisterRequest;
import com.example.compliancerag.entity.Role;
import com.example.compliancerag.entity.User;
import com.example.compliancerag.repository.UserRepository;
import com.example.compliancerag.security.JwtService;
import lombok.RequiredArgsConstructor;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;

@Service
@RequiredArgsConstructor
public class AuthenticationService {

    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;
    private final JwtService jwtService;
    private final AuthenticationManager authenticationManager;

    public AuthResponse register(RegisterRequest request) {
        if (userRepository.existsByUsername(request.username())) {
            throw new RuntimeException("Username already exists");
        }
        if (userRepository.existsByEmail(request.email())) {
            throw new RuntimeException("Email already exists");
        }

        var user = User.builder()
                .username(request.username())
                .email(request.email())
                .password(passwordEncoder.encode(request.password()))
                .role(Role.USER)
                .enabled(true)
                .build();

        userRepository.save(user);
        var jwtToken = jwtService.generateToken(user);
        
        return new AuthResponse(
                jwtToken,
                user.getUsername(),
                user.getEmail(),
                user.getRole().name()
        );
    }

    public AuthResponse login(LoginRequest request) {
        authenticationManager.authenticate(
                new UsernamePasswordAuthenticationToken(
                        request.username(),
                        request.password()
                )
        );

        var user = userRepository.findByUsername(request.username())
                .orElseThrow(() -> new RuntimeException("User not found"));

        var jwtToken = jwtService.generateToken(user);
        
        return new AuthResponse(
                jwtToken,
                user.getUsername(),
                user.getEmail(),
                user.getRole().name()
        );
    }
}
