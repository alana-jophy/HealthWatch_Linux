package com.healthwatch.data;

import com.google.gson.Gson;
import com.healthwatch.data.model.AuthModels.LoginRequest;
import com.healthwatch.data.model.AuthModels.TokenResponse;
import com.healthwatch.data.model.AuthModels.UserResponse;
import org.junit.Assert;
import org.junit.Before;
import org.junit.Test;

public class AuthSerializationTest {

    private Gson gson;

    @Before
    public void setUp() {
        gson = new Gson();
    }

    @Test
    public void testTokenResponseDeserialization_Success() {
        String backendJson = "{\n" +
                "  \"access_token\": \"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0In0.signature\",\n" +
                "  \"token_type\": \"bearer\",\n" +
                "  \"expires_in\": 3600,\n" +
                "  \"user\": {\n" +
                "    \"id\": \"98a3b379-3171-460d-a3df-616198fbb984\",\n" +
                "    \"email\": \"alanapj161@gmail.com\",\n" +
                "    \"full_name\": \"Alana P J\",\n" +
                "    \"role\": \"PATIENT\",\n" +
                "    \"is_active\": true,\n" +
                "    \"is_superuser\": false,\n" +
                "    \"patient_pseudo_id\": \"PAT-111\",\n" +
                "    \"patient_id\": \"765e4321-e89b-12d3-a456-426614174000\"\n" +
                "  }\n" +
                "}";

        TokenResponse tokenResponse = gson.fromJson(backendJson, TokenResponse.class);

        Assert.assertNotNull("TokenResponse should not be null", tokenResponse);
        Assert.assertEquals("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0In0.signature", tokenResponse.getAccessToken());
        Assert.assertEquals("bearer", tokenResponse.getTokenType());
        Assert.assertEquals(Long.valueOf(3600), tokenResponse.getExpiresIn());

        UserResponse user = tokenResponse.getUser();
        Assert.assertNotNull("UserResponse should not be null", user);
        Assert.assertEquals("98a3b379-3171-460d-a3df-616198fbb984", user.getId());
        Assert.assertEquals("alanapj161@gmail.com", user.getEmail());
        Assert.assertEquals("Alana P J", user.getFullName());
        Assert.assertEquals("PATIENT", user.getRole());
        Assert.assertTrue(user.isActive());
        Assert.assertFalse(user.isSuperuser());
        Assert.assertEquals("PAT-111", user.getPatientPseudoId());
        Assert.assertEquals("765e4321-e89b-12d3-a456-426614174000", user.getPatientId());
    }

    @Test
    public void testLoginRequestSerialization() {
        LoginRequest request = new LoginRequest("patient@healthwatch.org", "SecurePassword123!");
        String json = gson.toJson(request);

        Assert.assertTrue(json.contains("\"email\":\"patient@healthwatch.org\""));
        Assert.assertTrue(json.contains("\"password\":\"SecurePassword123!\""));
    }

    @Test
    public void testIncompleteUserValidation() {
        String backendJsonWithoutEmail = "{\n" +
                "  \"access_token\": \"valid-token\",\n" +
                "  \"user\": {\n" +
                "    \"id\": \"123\",\n" +
                "    \"role\": \"PATIENT\"\n" +
                "  }\n" +
                "}";

        TokenResponse tokenResponse = gson.fromJson(backendJsonWithoutEmail, TokenResponse.class);
        Assert.assertNotNull(tokenResponse);
        UserResponse user = tokenResponse.getUser();
        Assert.assertNotNull(user);

        // Verify null check detection
        boolean hasValidEmail = user.getEmail() != null && !user.getEmail().trim().isEmpty();
        Assert.assertFalse("User without email must be flagged as invalid", hasValidEmail);
    }
}
