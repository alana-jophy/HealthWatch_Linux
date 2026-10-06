package com.healthwatch.data.model;

import com.google.gson.annotations.SerializedName;
import java.util.ArrayList;
import java.util.List;

public class PatientModels {

    public static class PatientProfile {
        @SerializedName("id")
        private String id;

        @SerializedName("pseudo_id")
        private String pseudoId;

        @SerializedName("user_id")
        private String userId;

        @SerializedName("full_name")
        private String fullName;

        @SerializedName("age")
        private int age;

        @SerializedName("gender")
        private String gender;

        @SerializedName("contact_number")
        private String contactNumber;

        @SerializedName("address")
        private String address;

        @SerializedName("district_name")
        private String districtName;

        @SerializedName("local_body_name")
        private String localBodyName;

        @SerializedName("ward_number")
        private int wardNumber;

        @SerializedName("is_active")
        private boolean isActive;

        @SerializedName("monitoring_days")
        private Integer monitoringDays;

        public PatientProfile() {}

        public String getId() { return id; }
        public void setId(String id) { this.id = id; }

        public String getPseudoId() { return pseudoId; }
        public void setPseudoId(String pseudoId) { this.pseudoId = pseudoId; }

        public String getUserId() { return userId; }
        public void setUserId(String userId) { this.userId = userId; }

        public String getFullName() { return fullName; }
        public void setFullName(String fullName) { this.fullName = fullName; }

        public int getAge() { return age; }
        public void setAge(int age) { this.age = age; }

        public String getGender() { return gender; }
        public void setGender(String gender) { this.gender = gender; }

        public String getContactNumber() { return contactNumber; }
        public void setContactNumber(String contactNumber) { this.contactNumber = contactNumber; }

        public String getAddress() { return address; }
        public void setAddress(String address) { this.address = address; }

        public String getDistrictName() { return districtName; }
        public void setDistrictName(String districtName) { this.districtName = districtName; }

        public String getLocalBodyName() { return localBodyName; }
        public void setLocalBodyName(String localBodyName) { this.localBodyName = localBodyName; }

        public int getWardNumber() { return wardNumber; }
        public void setWardNumber(int wardNumber) { this.wardNumber = wardNumber; }

        public boolean isActive() { return isActive; }
        public void setActive(boolean active) { isActive = active; }

        public Integer getMonitoringDays() { return monitoringDays != null ? monitoringDays : 14; }
        public void setMonitoringDays(Integer monitoringDays) { this.monitoringDays = monitoringDays; }
    }

    public static class DiseaseCase {
        @SerializedName("id")
        private String id;

        @SerializedName("patient_id")
        private String patientId;

        @SerializedName("disease_id")
        private String diseaseId;

        @SerializedName("case_status")
        private String caseStatus;

        @SerializedName("severity")
        private String severity;

        @SerializedName("diagnosis_date")
        private String diagnosisDate;

        @SerializedName("latitude")
        private Double latitude;

        @SerializedName("longitude")
        private Double longitude;

        @SerializedName("source")
        private String source;

        @SerializedName("clinical_notes")
        private String clinicalNotes;

        @SerializedName("disease")
        private DiseaseInfo disease;

        public DiseaseCase() {}

        public String getId() { return id; }
        public void setId(String id) { this.id = id; }

        public String getPatientId() { return patientId; }
        public void setPatientId(String patientId) { this.patientId = patientId; }

        public String getDiseaseId() { return diseaseId; }
        public void setDiseaseId(String diseaseId) { this.diseaseId = diseaseId; }

        public String getCaseStatus() { return caseStatus; }
        public void setCaseStatus(String caseStatus) { this.caseStatus = caseStatus; }

        public String getSeverity() { return severity; }
        public void setSeverity(String severity) { this.severity = severity; }

        public String getDiagnosisDate() { return diagnosisDate; }
        public void setDiagnosisDate(String diagnosisDate) { this.diagnosisDate = diagnosisDate; }

        public Double getLatitude() { return latitude; }
        public void setLatitude(Double latitude) { this.latitude = latitude; }

        public Double getLongitude() { return longitude; }
        public void setLongitude(Double longitude) { this.longitude = longitude; }

        public String getSource() { return source; }
        public void setSource(String source) { this.source = source; }

        public String getClinicalNotes() { return clinicalNotes; }
        public void setClinicalNotes(String clinicalNotes) { this.clinicalNotes = clinicalNotes; }

        public DiseaseInfo getDisease() { return disease; }
        public void setDisease(DiseaseInfo disease) { this.disease = disease; }
    }

    public static class DiseaseInfo {
        @SerializedName("id")
        private String id;

        @SerializedName("code")
        private String code;

        @SerializedName("name")
        private String name;

        @SerializedName("contagion_type")
        private String contagionType;

        @SerializedName("category")
        private String category;

        @SerializedName("incubation_period_days")
        private int incubationPeriodDays;

        public DiseaseInfo() {}

        public String getId() { return id; }
        public void setId(String id) { this.id = id; }

        public String getCode() { return code; }
        public void setCode(String code) { this.code = code; }

        public String getName() { return name; }
        public void setName(String name) { this.name = name; }

        public String getContagionType() { return contagionType; }
        public void setContagionType(String contagionType) { this.contagionType = contagionType; }

        public String getCategory() { return category; }
        public void setCategory(String category) { this.category = category; }

        public int getIncubationPeriodDays() { return incubationPeriodDays; }
        public void setIncubationPeriodDays(int incubationPeriodDays) { this.incubationPeriodDays = incubationPeriodDays; }
    }

    public static class PaginatedResponse<T> {
        @SerializedName("total")
        private int total;

        @SerializedName("items")
        private List<T> items = new ArrayList<>();

        public PaginatedResponse() {}

        public int getTotal() { return total; }
        public void setTotal(int total) { this.total = total; }

        public List<T> getItems() { return items != null ? items : new ArrayList<T>(); }
        public void setItems(List<T> items) { this.items = items; }
    }
}
