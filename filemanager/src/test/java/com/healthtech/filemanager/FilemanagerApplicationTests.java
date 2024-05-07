package com.healthtech.filemanager;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.client.TestRestTemplate;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;

import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
class FilemanagerApplicationTests {

	@Autowired
	TestRestTemplate restTemplate;

	@Test
	void contextLoads() {
		assertThat(1).isEqualTo(1);
	}

	@Test
	void shouldReturnExames() {
		ResponseEntity<String> response = restTemplate.getForEntity("/exames/01", String.class);

		assertThat(response.getStatusCode()).isEqualTo(HttpStatus.OK);

	}

}
