package com.healthtech.filemanager.controller;

import org.apache.coyote.Response;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
    @RequestMapping("/exames")
public class ExameController {

    @GetMapping("/{usuarioId}")
    private ResponseEntity<String> findById() {
        return ResponseEntity.ok("{}");
    }
}
