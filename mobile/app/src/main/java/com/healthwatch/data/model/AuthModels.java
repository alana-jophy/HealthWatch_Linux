package com.healthwatch.data.model;

import com.google.gson.annotations.SerializedName;

public class AuthModels {

    public static class LoginRequest {
        @SerializedName("email")
        private String email;

        @SerializedName("password")
        private String password;

        public LoginRequest() {}

        public LoginRequest(String email, String password) {
            this.email = email;
            this.password = password;
        }

        public String getEmail() {
            return email;
        }

        public void setEmail(String email) {
            this.email = email;
        }

        public String getPassword() {
            return password;
        }

        public void setPassword(String password) {
            this.password = password;
        }
    }

    public static class UserResponse {
        @SerializedName("id")
        private String id;

        @SerializedName("email")
        private String email;

        @SerializedName("full_name")
        private String fullName;

        @SerializedName("role")
        private String role;

        @SerializedName("is_active")
        private boolean isActive = true;

        @SerializedName("is_superuser")
        private boolean isSuperuser = false;

        @SerializedName("patient_pseudo_id")
        private String patientPseudoId;

        @SerializedName("patient_id")
        private String patientId;

        public UserResponse() {}

        public String getId() {
            return id;
        }

        public void setId(String id) {
            this.id = id;
        }

        public String getEmail() {
            return email;
        }

        public void setEmail(String email) {
            this.email = email;
        }

        public String getFullName() {
            return fullName != null ? fullName : "";
        }

        public void setFullName(String fullName) {
            this.fullName = fullName;
        }

        public String getRole() {
            return role != null ? role : "";
        }

        public void setRole(String role) {
            this.role = role;
        }

        public boolean isActive() {
            return isActive;
        }

        public void setActive(boolean active) {
            isActive = active;
        }

        public boolean isSuperuser() {
            return isSuperuser;
        }

        public void setSuperuser(boolean superuser) {
            isSuperuser = superuser;
        }

        public String getPatientPseudoId() {
            return patientPseudoId;
        }

        public void setPatientPseudoId(String patientPseudoId) {
            this.patientPseudoId = patientPseudoId;
        }

        public String getPatientId() {
            return patientId;
        }

        public void setPatientId(String patientId) {
            this.patientId = patientId;
        }
    }

    public static class TokenResponse {
        @SerializedName("access_token")
        private String accessToken;

        @SerializedName("token_type")
        private String tokenType = "bearer";

        @SerializedName("expires_in")
        private Long expiresIn = 0L;

        @SerializedName("user")
        private UserResponse user;

        public TokenResponse() {}

        public String getAccessToken() {
            return accessToken;
        }

        public void setAccessToken(String accessToken) {
            this.accessToken = accessToken;
        }

        public String getTokenType() {
            return tokenType;
        }

        public void setTokenType(String tokenType) {
            this.tokenType = tokenType;
        }

        public Long getExpiresIn() {
            return expiresIn;
        }

        public void setExpiresIn(Long expiresIn) {
            this.expiresIn = expiresIn;
        }

        public UserResponse getUser() {
            return user;
        }

        public void setUser(UserResponse user) {
            this.user = user;
        }
    }
}
