import datetime
import uuid
from loguru import logger
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.db.base import Base
from app.db.session import engine, SessionLocal
from app.models.disease import CaseStatus, ContagionType, Disease, DiseaseCase
from app.models.monitoring import LocationConsent, MonitoringSession, PatientLocation
from app.models.patient import Patient
from app.models.spatial import District, LocalBody, Ward
from app.models.user import Role, User
from app.models.exposure import ExposureEvent, ExposureStatus
from app.schemas.auth import RoleEnum


# Initial synthetic roles
INITIAL_ROLES = [
    {"name": RoleEnum.ADMIN.value, "description": "System Administrator with full platform control"},
    {"name": RoleEnum.PUBLIC_HEALTH_OFFICER.value, "description": "Surveillance Lead & Epidemiological Decision Maker"},
    {"name": RoleEnum.HEALTH_WORKER.value, "description": "Field Worker managing case reports & patient contact tracing"},
    {"name": RoleEnum.PATIENT.value, "description": "Patient user under authorized quarantine/surveillance"},
]

# Initial synthetic test users
SYNTHETIC_USERS = [
    {
        "email": "admin@healthwatch.org",
        "password": "Admin@HealthWatch2026",
        "full_name": "System Administrator",
        "role": RoleEnum.ADMIN.value,
        "is_superuser": True,
    },
    {
        "email": "officer.surveillance@healthwatch.org",
        "password": "Officer@HealthWatch2026",
        "full_name": "Dr. Sarah Mitchell (Lead Epidemiologist)",
        "role": RoleEnum.PUBLIC_HEALTH_OFFICER.value,
        "is_superuser": False,
    },
    {
        "email": "worker.field01@healthwatch.org",
        "password": "Worker@HealthWatch2026",
        "full_name": "Rajesh Kumar (Field Surveillance Officer)",
        "role": RoleEnum.HEALTH_WORKER.value,
        "is_superuser": False,
    },
    {
        "email": "officer@test.com",
        "password": "Officer@123",
        "full_name": "Dr. Test Officer (Surveillance Lead)",
        "role": RoleEnum.PUBLIC_HEALTH_OFFICER.value,
        "is_superuser": False,
    },
    {
        "email": "alana@healthwatch.org",
        "password": "Patient@HealthWatch2026",
        "full_name": "Alana P J",
        "role": RoleEnum.PATIENT.value,
        "is_superuser": False,
    },
]

# Synthetic disease catalog
SYNTHETIC_DISEASES = [
    {
        "code": "DENGUE-01",
        "name": "Dengue Fever",
        "contagion_type": ContagionType.CONTAGIOUS.value,
        "category": "Vector-Borne",
        "incubation_period_days": 7,
        "r0_estimate": 1.8,
        "description": "Mosquito-borne viral infection causing high fever, joint pain, and potential hemorrhagic complications.",
    },
    {
        "code": "COVID-19",
        "name": "Coronavirus Disease 2019",
        "contagion_type": ContagionType.CONTAGIOUS.value,
        "category": "Respiratory",
        "incubation_period_days": 5,
        "r0_estimate": 2.5,
        "description": "Contagious respiratory disease caused by the SARS-CoV-2 virus.",
    },
    {
        "code": "CHOLERA-01",
        "name": "Cholera Outbreak Strain",
        "contagion_type": ContagionType.CONTAGIOUS.value,
        "category": "Water-Borne",
        "incubation_period_days": 2,
        "r0_estimate": 2.1,
        "description": "Acute diarrheal infection caused by ingestion of food or water contaminated with Vibrio cholerae.",
    },
    {
        "code": "DIABETES-T2",
        "name": "Type 2 Diabetes Mellitus",
        "contagion_type": ContagionType.NON_CONTAGIOUS.value,
        "category": "Metabolic",
        "incubation_period_days": 30,
        "r0_estimate": 0.0,
        "description": "Chronic metabolic condition characterized by insulin resistance and hyperglycemia.",
    },
    {
        "code": "HYPERTENSION",
        "name": "Essential Hypertension",
        "contagion_type": ContagionType.NON_CONTAGIOUS.value,
        "category": "Cardiovascular",
        "incubation_period_days": 30,
        "r0_estimate": 0.0,
        "description": "Chronic medical condition in which the blood pressure in the arteries is persistently elevated.",
    },
]

# Kerala GIS Hierarchy (All 14 Official Districts + Demonstration Local Bodies & Wards)
# NOTE: Local body and ward geometries represent synthetic approximations for academic surveillance demonstration,
# and do not claim to be official government land survey GIS boundaries.
SYNTHETIC_DISTRICTS = [
    {
        "code": "KL-ALP",
        "name": "Alappuzha",
        "state": "Kerala",
        "lat": 9.4981,
        "lng": 76.3388,
        "local_bodies": [
            {
                "name": "Alappuzha Municipality",
                "type": "Municipality",
                "lat": 9.4981,
                "lng": 76.3388,
                "wards": [
                    {"number": 1, "name": "Alappuzha Beach Ward", "lat": 9.4950, "lng": 76.3250},
                    {"number": 2, "name": "Mullakkal Ward", "lat": 9.4920, "lng": 76.3350},
                ],
            }
        ],
    },
    {
        "code": "KL-EKM",
        "name": "Ernakulam",
        "state": "Kerala",
        "lat": 9.9816,
        "lng": 76.2999,
        "local_bodies": [
            {
                "name": "Kochi Municipal Corporation",
                "type": "Corporation",
                "lat": 9.9675,
                "lng": 76.2422,
                "wards": [
                    {"number": 5, "name": "Marine Drive Ward", "lat": 9.9780, "lng": 76.2750},
                    {"number": 6, "name": "Edappally Ward", "lat": 10.0240, "lng": 76.3080},
                ],
            }
        ],
    },
    {
        "code": "KL-IDK",
        "name": "Idukki",
        "state": "Kerala",
        "lat": 9.8494,
        "lng": 76.9806,
        "local_bodies": [
            {
                "name": "Thodupuzha Municipality",
                "type": "Municipality",
                "lat": 9.8959,
                "lng": 76.7184,
                "wards": [
                    {"number": 1, "name": "Thodupuzha Town Ward", "lat": 9.8950, "lng": 76.7180},
                    {"number": 2, "name": "Vengalloor Ward", "lat": 9.9020, "lng": 76.7250},
                ],
            }
        ],
    },
    {
        "code": "KL-KNR",
        "name": "Kannur",
        "state": "Kerala",
        "lat": 11.8745,
        "lng": 75.3704,
        "local_bodies": [
            {
                "name": "Kannur Municipal Corporation",
                "type": "Corporation",
                "lat": 11.8745,
                "lng": 75.3704,
                "wards": [
                    {"number": 1, "name": "Camp Bazaar Ward", "lat": 11.8720, "lng": 75.3710},
                    {"number": 2, "name": "Payyambalam Ward", "lat": 11.8680, "lng": 75.3580},
                ],
            }
        ],
    },
    {
        "code": "KL-KSD",
        "name": "Kasaragod",
        "state": "Kerala",
        "lat": 12.5102,
        "lng": 74.9852,
        "local_bodies": [
            {
                "name": "Kasaragod Municipality",
                "type": "Municipality",
                "lat": 12.5102,
                "lng": 74.9852,
                "wards": [
                    {"number": 1, "name": "Kasaragod Town Ward", "lat": 12.5090, "lng": 74.9860},
                    {"number": 2, "name": "Vidyanagar Ward", "lat": 12.5180, "lng": 75.0020},
                ],
            }
        ],
    },
    {
        "code": "KL-KLM",
        "name": "Kollam",
        "state": "Kerala",
        "lat": 8.8932,
        "lng": 76.6141,
        "local_bodies": [
            {
                "name": "Kollam Municipal Corporation",
                "type": "Corporation",
                "lat": 8.8932,
                "lng": 76.6141,
                "wards": [
                    {"number": 1, "name": "Chinnakada Ward", "lat": 8.8880, "lng": 76.5910},
                    {"number": 2, "name": "Asramam Ward", "lat": 8.9010, "lng": 76.6020},
                ],
            }
        ],
    },
    {
        "code": "KL-KTM",
        "name": "Kottayam",
        "state": "Kerala",
        "lat": 9.5916,
        "lng": 76.5222,
        "local_bodies": [
            {
                "name": "Kottayam Municipality",
                "type": "Municipality",
                "lat": 9.5916,
                "lng": 76.5222,
                "wards": [
                    {"number": 1, "name": "Thirunakkara Ward", "lat": 9.5900, "lng": 76.5210},
                    {"number": 2, "name": "Nagampadam Ward", "lat": 9.6010, "lng": 76.5310},
                ],
            }
        ],
    },
    {
        "code": "KL-KKD",
        "name": "Kozhikode",
        "state": "Kerala",
        "lat": 11.2588,
        "lng": 75.7804,
        "local_bodies": [
            {
                "name": "Kozhikode Municipal Corporation",
                "type": "Corporation",
                "lat": 11.2500,
                "lng": 75.7700,
                "wards": [
                    {"number": 7, "name": "Mananchira Ward", "lat": 11.2540, "lng": 75.7820},
                    {"number": 8, "name": "Palayam Ward (Kozhikode)", "lat": 11.2510, "lng": 75.7840},
                ],
            }
        ],
    },
    {
        "code": "KL-MLP",
        "name": "Malappuram",
        "state": "Kerala",
        "lat": 11.0735,
        "lng": 76.0740,
        "local_bodies": [
            {
                "name": "Malappuram Municipality",
                "type": "Municipality",
                "lat": 11.0735,
                "lng": 76.0740,
                "wards": [
                    {"number": 1, "name": "Down Hill Ward", "lat": 11.0680, "lng": 76.0690},
                    {"number": 2, "name": "Up Hill Ward", "lat": 11.0760, "lng": 76.0790},
                ],
            }
        ],
    },
    {
        "code": "KL-PKD",
        "name": "Palakkad",
        "state": "Kerala",
        "lat": 10.7867,
        "lng": 76.6548,
        "local_bodies": [
            {
                "name": "Palakkad Municipality",
                "type": "Municipality",
                "lat": 10.7867,
                "lng": 76.6548,
                "wards": [
                    {"number": 1, "name": "Fort Maidan Ward", "lat": 10.7710, "lng": 76.6550},
                    {"number": 2, "name": "Sulthanpet Ward", "lat": 10.7780, "lng": 76.6520},
                ],
            }
        ],
    },
    {
        "code": "KL-PTA",
        "name": "Pathanamthitta",
        "state": "Kerala",
        "lat": 9.2648,
        "lng": 76.7870,
        "local_bodies": [
            {
                "name": "Pathanamthitta Municipality",
                "type": "Municipality",
                "lat": 9.2648,
                "lng": 76.7870,
                "wards": [
                    {"number": 1, "name": "Pathanamthitta Town Ward", "lat": 9.2630, "lng": 76.7860},
                    {"number": 2, "name": "Kumbazha Ward", "lat": 9.2690, "lng": 76.8010},
                ],
            }
        ],
    },
    {
        "code": "KL-TVM",
        "name": "Thiruvananthapuram",
        "state": "Kerala",
        "lat": 8.5241,
        "lng": 76.9366,
        "local_bodies": [
            {
                "name": "Thiruvananthapuram Municipal Corporation",
                "type": "Corporation",
                "lat": 8.5061,
                "lng": 76.9558,
                "wards": [
                    {"number": 1, "name": "Palayam Ward", "lat": 8.5020, "lng": 76.9510},
                    {"number": 2, "name": "Medical College Ward", "lat": 8.5240, "lng": 76.9280},
                    {"number": 3, "name": "Fort Ward", "lat": 8.4830, "lng": 76.9450},
                    {"number": 4, "name": "Pattom Ward", "lat": 8.5290, "lng": 76.9420},
                ],
            },
            {
                "name": "Nedumangad Municipality",
                "type": "Municipality",
                "lat": 8.6041,
                "lng": 77.0025,
                "wards": [
                    {"number": 1, "name": "Town Ward", "lat": 8.6040, "lng": 77.0020},
                    {"number": 2, "name": "Valavur Ward", "lat": 8.6120, "lng": 77.0150},
                ],
            },
        ],
    },
    {
        "code": "KL-TCR",
        "name": "Thrissur",
        "state": "Kerala",
        "lat": 10.5276,
        "lng": 76.2144,
        "local_bodies": [
            {
                "name": "Thrissur Municipal Corporation",
                "type": "Corporation",
                "lat": 10.5276,
                "lng": 76.2144,
                "wards": [
                    {"number": 1, "name": "Swaraj Round Ward", "lat": 10.5240, "lng": 76.2140},
                    {"number": 2, "name": "Ayyanthole Ward", "lat": 10.5310, "lng": 76.1950},
                ],
            }
        ],
    },
    {
        "code": "KL-WYD",
        "name": "Wayanad",
        "state": "Kerala",
        "lat": 11.6854,
        "lng": 76.1320,
        "local_bodies": [
            {
                "name": "Kalpetta Municipality",
                "type": "Municipality",
                "lat": 11.6050,
                "lng": 76.0830,
                "wards": [
                    {"number": 1, "name": "Kalpetta Town Ward", "lat": 11.6040, "lng": 76.0820},
                    {"number": 2, "name": "Madiyur Ward", "lat": 11.6110, "lng": 76.0910},
                ],
            }
        ],
    },
]

# Monitored Patient Registry (Single Patient)
SYNTHETIC_PATIENTS = [
    {
        "pseudo_id": "PAT-USER-143",
        "user_email": "alana@healthwatch.org",
        "assigned_worker_email": "worker.field01@healthwatch.org",
        "full_name": "Alana P J",
        "age": 21,
        "gender": "FEMALE",
        "has_phone": True,
        "contact_number": "8136963623",
        "disease_code": "DENGUE-01",
        "address": "PULIKKOTTIL HOUSE, PADIVARAMBU, ELAVALLY",
        "district_name": "Thrissur",
        "local_body_name": "Elavally Grama Panchayat",
        "ward_number": 17,
    },
]


def sync_schema_columns(conn) -> None:
    """Execute non-destructive schema migrations for newly introduced model columns."""
    migration_statements = [
        # District spatial columns
        "ALTER TABLE districts ADD COLUMN IF NOT EXISTS center_latitude FLOAT;",
        "ALTER TABLE districts ADD COLUMN IF NOT EXISTS center_longitude FLOAT;",
        "ALTER TABLE districts ADD COLUMN IF NOT EXISTS source VARCHAR(50) DEFAULT 'SIMULATED';",
        
        # Local body spatial columns
        "ALTER TABLE local_bodies ADD COLUMN IF NOT EXISTS code VARCHAR(50);",
        "ALTER TABLE local_bodies ADD COLUMN IF NOT EXISTS center_latitude FLOAT;",
        "ALTER TABLE local_bodies ADD COLUMN IF NOT EXISTS center_longitude FLOAT;",
        "ALTER TABLE local_bodies ADD COLUMN IF NOT EXISTS source VARCHAR(50) DEFAULT 'OFFICIAL_SEC';",
        "CREATE INDEX IF NOT EXISTS ix_local_bodies_code ON local_bodies(code);",
        
        # Ward spatial columns
        "ALTER TABLE wards ADD COLUMN IF NOT EXISTS ward_code VARCHAR(50);",
        "ALTER TABLE wards ADD COLUMN IF NOT EXISTS center_latitude FLOAT;",
        "ALTER TABLE wards ADD COLUMN IF NOT EXISTS center_longitude FLOAT;",
        "ALTER TABLE wards ADD COLUMN IF NOT EXISTS source VARCHAR(50) DEFAULT 'OFFICIAL_SEC';",
        "CREATE INDEX IF NOT EXISTS ix_wards_ward_code ON wards(ward_code);",
        "CREATE INDEX IF NOT EXISTS ix_wards_lb_wn ON wards(local_body_id, ward_number);",
        
        # Disease case spatial columns
        "ALTER TABLE disease_cases ADD COLUMN IF NOT EXISTS ward_id UUID REFERENCES wards(id) ON DELETE SET NULL;",
        "ALTER TABLE disease_cases ADD COLUMN IF NOT EXISTS location GEOGRAPHY(POINT, 4326);",
        "ALTER TABLE disease_cases ADD COLUMN IF NOT EXISTS latitude FLOAT;",
        "ALTER TABLE disease_cases ADD COLUMN IF NOT EXISTS longitude FLOAT;",
        "ALTER TABLE disease_cases ADD COLUMN IF NOT EXISTS source VARCHAR(50) DEFAULT 'SIMULATED';",
        "ALTER TABLE disease_cases ALTER COLUMN status DROP NOT NULL;",

        # Location Consent columns
        "ALTER TABLE location_consents ADD COLUMN IF NOT EXISTS consent_status VARCHAR(50) DEFAULT 'ACTIVE';",
        "ALTER TABLE location_consents ADD COLUMN IF NOT EXISTS consent_given_at TIMESTAMPTZ DEFAULT NOW();",
        "ALTER TABLE location_consents ADD COLUMN IF NOT EXISTS consent_version VARCHAR(20) DEFAULT 'v1.0';",
        "ALTER TABLE location_consents ADD COLUMN IF NOT EXISTS monitoring_start TIMESTAMPTZ DEFAULT NOW();",
        "ALTER TABLE location_consents ADD COLUMN IF NOT EXISTS monitoring_end TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '14 days');",
        "ALTER TABLE location_consents ADD COLUMN IF NOT EXISTS revoked_at TIMESTAMPTZ;",
        "ALTER TABLE location_consents ADD COLUMN IF NOT EXISTS purpose VARCHAR(255) DEFAULT 'Authorized Quarantine Compliance & Outbreak Contact Surveillance (approx. every 15 mins)';",
        "ALTER TABLE location_consents ALTER COLUMN consent_granted DROP NOT NULL;",
        "ALTER TABLE location_consents ALTER COLUMN consent_date DROP NOT NULL;",

        # Monitoring Session columns
        "ALTER TABLE monitoring_sessions ADD COLUMN IF NOT EXISTS consent_id UUID REFERENCES location_consents(id) ON DELETE CASCADE;",
        "ALTER TABLE monitoring_sessions ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'ACTIVE';",
        "ALTER TABLE monitoring_sessions ADD COLUMN IF NOT EXISTS stopped_at TIMESTAMPTZ;",
        "ALTER TABLE monitoring_sessions ALTER COLUMN session_status DROP NOT NULL;",
        "ALTER TABLE monitoring_sessions ALTER COLUMN end_time DROP NOT NULL;",
        "ALTER TABLE monitoring_sessions ALTER COLUMN sync_frequency_seconds DROP NOT NULL;",

        # Patient Locations columns
        "ALTER TABLE patient_locations ADD COLUMN IF NOT EXISTS source VARCHAR(50) DEFAULT 'PATIENT_GPS';",
        "ALTER TABLE patient_locations ALTER COLUMN location DROP NOT NULL;",
        "ALTER TABLE patient_locations ADD COLUMN IF NOT EXISTS monitoring_session_id UUID REFERENCES monitoring_sessions(id) ON DELETE CASCADE;",
        "ALTER TABLE patient_locations ADD COLUMN IF NOT EXISTS accuracy FLOAT;",
        "ALTER TABLE patient_locations ADD COLUMN IF NOT EXISTS location_geography GEOGRAPHY(POINT, 4326);",
        "ALTER TABLE patient_locations ADD COLUMN IF NOT EXISTS client_observation_id VARCHAR(100);",
        "UPDATE patient_locations SET monitoring_session_id = session_id WHERE monitoring_session_id IS NULL;",
        "UPDATE patient_locations SET accuracy = accuracy_meters WHERE accuracy IS NULL;",
        "UPDATE patient_locations SET location_geography = location::geography WHERE location_geography IS NULL AND location IS NOT NULL;",

        # Patient assigned health worker column, phone status, and disease linkage
        "ALTER TABLE patients ADD COLUMN IF NOT EXISTS assigned_worker_id UUID REFERENCES users(id) ON DELETE SET NULL;",
        "ALTER TABLE patients ADD COLUMN IF NOT EXISTS has_phone BOOLEAN DEFAULT TRUE;",
        "ALTER TABLE patients ADD COLUMN IF NOT EXISTS disease_id UUID REFERENCES diseases(id) ON DELETE SET NULL;",
        "ALTER TABLE patients ADD COLUMN IF NOT EXISTS disease_name VARCHAR(100);",
        "ALTER TABLE monitoring_sessions ADD COLUMN IF NOT EXISTS sampling_interval_minutes INTEGER DEFAULT 15;",

        # Exposure Events columns (Step 16)
        "ALTER TABLE exposure_events ADD COLUMN IF NOT EXISTS patient_a_id UUID REFERENCES patients(id) ON DELETE CASCADE;",
        "ALTER TABLE exposure_events ADD COLUMN IF NOT EXISTS patient_b_id UUID REFERENCES patients(id) ON DELETE CASCADE;",
        "ALTER TABLE exposure_events ADD COLUMN IF NOT EXISTS observation_a_id UUID REFERENCES patient_locations(id) ON DELETE SET NULL;",
        "ALTER TABLE exposure_events ADD COLUMN IF NOT EXISTS observation_b_id UUID REFERENCES patient_locations(id) ON DELETE SET NULL;",
        "ALTER TABLE exposure_events ADD COLUMN IF NOT EXISTS observation_a_time TIMESTAMPTZ;",
        "ALTER TABLE exposure_events ADD COLUMN IF NOT EXISTS observation_b_time TIMESTAMPTZ;",
        "ALTER TABLE exposure_events ADD COLUMN IF NOT EXISTS latitude FLOAT;",
        "ALTER TABLE exposure_events ADD COLUMN IF NOT EXISTS longitude FLOAT;",
        "ALTER TABLE exposure_events ADD COLUMN IF NOT EXISTS distance FLOAT;",
        "ALTER TABLE exposure_events ADD COLUMN IF NOT EXISTS time_difference FLOAT;",
        "ALTER TABLE exposure_events ADD COLUMN IF NOT EXISTS confidence_score FLOAT DEFAULT 0.5;",
        "ALTER TABLE exposure_events ADD COLUMN IF NOT EXISTS review_notes TEXT;",
        "ALTER TABLE exposure_events ADD COLUMN IF NOT EXISTS reviewed_by_id UUID REFERENCES users(id) ON DELETE SET NULL;",
        "ALTER TABLE exposure_events ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMPTZ;",
        "ALTER TABLE exposure_events ALTER COLUMN source_patient_id DROP NOT NULL;",
        "ALTER TABLE exposure_events ALTER COLUMN exposed_entity_token DROP NOT NULL;",
        "ALTER TABLE exposure_events ALTER COLUMN distance_meters DROP NOT NULL;",
        "ALTER TABLE exposure_events ALTER COLUMN duration_minutes DROP NOT NULL;",
        "ALTER TABLE exposure_events ALTER COLUMN risk_score DROP NOT NULL;",
        "UPDATE exposure_events SET distance = distance_meters WHERE distance IS NULL AND distance_meters IS NOT NULL;",
        "UPDATE exposure_events SET time_difference = duration_minutes WHERE time_difference IS NULL AND duration_minutes IS NOT NULL;",
        "UPDATE exposure_events SET confidence_score = risk_score WHERE confidence_score IS NULL AND risk_score IS NOT NULL;",
    ]

    for stmt in migration_statements:
        try:
            conn.execute(text(stmt))
        except Exception as e:
            logger.debug(f"Schema sync notice on [{stmt}]: {e}")


def make_synthetic_polygon(center_lng: float, center_lat: float, radius: float = 0.015) -> str:
    """Create a simulated MultiPolygon WKT around a center coordinate."""
    p1 = f"{center_lng - radius} {center_lat - radius}"
    p2 = f"{center_lng + radius} {center_lat - radius}"
    p3 = f"{center_lng + radius} {center_lat + radius}"
    p4 = f"{center_lng - radius} {center_lat + radius}"
    p5 = p1
    return f"MULTIPOLYGON((({p1}, {p2}, {p3}, {p4}, {p5})))"


def init_db(db: Session = None) -> None:
    """Initialize database tables, spatial hierarchy, roles, diseases, patients, and cases."""
    try:
        # Create all tables if not existing
        Base.metadata.create_all(bind=engine)

        # Apply schema columns update
        with engine.connect() as conn:
            sync_schema_columns(conn)
            conn.commit()

        logger.info("Database tables and spatial columns synchronized.")

        close_session = False
        if db is None:
            db = SessionLocal()
            close_session = True

        try:
            # 1. Seed Roles
            role_map = {}
            for r_data in INITIAL_ROLES:
                role = db.query(Role).filter(Role.name == r_data["name"]).first()
                if not role:
                    role = Role(name=r_data["name"], description=r_data["description"])
                    db.add(role)
                    db.flush()
                role_map[role.name] = role
            db.commit()

            # 2. Seed Synthetic Users
            user_map = {}
            for u_data in SYNTHETIC_USERS:
                user = db.query(User).filter(User.email == u_data["email"]).first()
                role_obj = role_map.get(u_data["role"])
                if not user:
                    user = User(
                        email=u_data["email"],
                        hashed_password=get_password_hash(u_data["password"]),
                        full_name=u_data["full_name"],
                        role_id=role_obj.id if role_obj else None,
                        is_active=True,
                        is_superuser=u_data["is_superuser"],
                    )
                    db.add(user)
                    db.flush()
                else:
                    user.hashed_password = get_password_hash(u_data["password"])
                    user.role_id = role_obj.id if role_obj else user.role_id
                    user.is_active = True
                    db.flush()
                user_map[user.email] = user
            db.commit()

            # 3. Seed Spatial Hierarchy (Kerala -> District -> LocalBody -> Ward)
            district_map = {}
            ward_map = {}

            # Check if official wards are already imported
            official_ward_count = db.query(Ward).filter(Ward.source == "OFFICIAL_SEC").count()
            if official_ward_count < 20000:
                logger.info(f"Official wards count is {official_ward_count}. Importing full official dataset...")
                try:
                    from app.scripts.import_official_kerala_wards import import_official_wards
                    import_official_wards()
                except Exception as e:
                    logger.warning(f"Could not import official wards script directly: {e}")

            for d in db.query(District).all():
                district_map[d.code] = d
                district_map[d.name] = d

            for w in db.query(Ward).limit(500).all():
                ward_map[w.name] = w


            # 4. Seed Synthetic Diseases
            disease_map = {}
            for d_data in SYNTHETIC_DISEASES:
                disease = db.query(Disease).filter(Disease.code == d_data["code"]).first()
                if not disease:
                    disease = Disease(
                        code=d_data["code"],
                        name=d_data["name"],
                        contagion_type=d_data["contagion_type"],
                        category=d_data["category"],
                        incubation_period_days=d_data["incubation_period_days"],
                        r0_estimate=d_data["r0_estimate"],
                        description=d_data["description"],
                        is_active=True,
                    )
                    db.add(disease)
                    db.flush()
                disease_map[disease.code] = disease
            db.commit()

            # 5. Seed Patient Registry (Single Patient)
            patient_map = {}
            for p_data in SYNTHETIC_PATIENTS:
                patient = db.query(Patient).filter(Patient.pseudo_id == p_data["pseudo_id"]).first()
                linked_user = user_map.get(p_data["user_email"]) if p_data.get("user_email") else None
                assigned_worker = user_map.get(p_data.get("assigned_worker_email")) if p_data.get("assigned_worker_email") else None
                assigned_worker_id = assigned_worker.id if assigned_worker else None

                thrissur = db.query(District).filter(District.name == "Thrissur").first()
                elavally = db.query(LocalBody).filter(LocalBody.code == "G08037").first() or db.query(LocalBody).filter(LocalBody.name.ilike("%Elavally%")).first()
                ward_17 = db.query(Ward).filter(Ward.ward_code == "G08037017").first() or (db.query(Ward).filter(Ward.local_body_id == elavally.id, Ward.ward_number == 17).first() if elavally else None)
                assigned_disease = disease_map.get(p_data.get("disease_code", "DENGUE-01"))

                if not patient:
                    patient = Patient(
                        pseudo_id=p_data["pseudo_id"],
                        user_id=linked_user.id if linked_user else None,
                        assigned_worker_id=assigned_worker_id,
                        full_name=p_data["full_name"],
                        age=p_data["age"],
                        gender=p_data["gender"],
                        has_phone=p_data.get("has_phone", True),
                        contact_number=p_data["contact_number"],
                        disease_id=assigned_disease.id if assigned_disease else None,
                        disease_name=assigned_disease.name if assigned_disease else None,
                        address=p_data["address"],
                        district_name=p_data["district_name"],
                        local_body_name=p_data["local_body_name"],
                        ward_number=p_data["ward_number"],
                        district_id=thrissur.id if thrissur else None,
                        local_body_id=elavally.id if elavally else None,
                        ward_id=ward_17.id if ward_17 else None,
                        is_active=True,
                    )
                    db.add(patient)
                    db.flush()
                else:
                    patient.assigned_worker_id = assigned_worker_id
                    patient.has_phone = p_data.get("has_phone", True)
                    patient.contact_number = p_data["contact_number"]
                    if assigned_disease:
                        patient.disease_id = assigned_disease.id
                        patient.disease_name = assigned_disease.name
                    if linked_user and not patient.user_id:
                        patient.user_id = linked_user.id
                    if thrissur and not patient.district_id:
                        patient.district_id = thrissur.id
                    if elavally and not patient.local_body_id:
                        patient.local_body_id = elavally.id
                    if ward_17 and not patient.ward_id:
                        patient.ward_id = ward_17.id
                    patient.is_active = True
                    db.flush()

                # Ensure a DiseaseCase exists for this patient
                if assigned_disease:
                    d_case = db.query(DiseaseCase).filter(
                        DiseaseCase.patient_id == patient.id,
                        DiseaseCase.disease_id == assigned_disease.id
                    ).first()
                    lat = ward_17.center_latitude if ward_17 and ward_17.center_latitude else 10.5833
                    lng = ward_17.center_longitude if ward_17 and ward_17.center_longitude else 76.0833
                    if not d_case:
                        d_case = DiseaseCase(
                            patient_id=patient.id,
                            disease_id=assigned_disease.id,
                            ward_id=ward_17.id if ward_17 else None,
                            case_status=CaseStatus.CONFIRMED.value,
                            severity="MODERATE",
                            diagnosis_date=datetime.date.today(),
                            latitude=lat,
                            longitude=lng,
                            source="SURVEILLANCE",
                            clinical_notes="Registered clinical case under active surveillance.",
                        )
                        db.add(d_case)
                        db.flush()
                    else:
                        d_case.ward_id = ward_17.id if ward_17 else d_case.ward_id
                        d_case.latitude = lat
                        d_case.longitude = lng
                        db.flush()

                patient_map[patient.pseudo_id] = patient
            db.commit()

            # 6. Seed Synthetic Disease Cases with Spatial Point Geography
            officer_user = user_map.get("officer.surveillance@healthwatch.org")
            case_definitions = []

            # Reset simulated cases for idempotent heatmap tier evaluation
            db.query(DiseaseCase).filter(DiseaseCase.source == "SIMULATED").delete()
            db.commit()

            for c_def in case_definitions:
                p_obj = patient_map.get(c_def["patient_pseudo"])
                d_obj = disease_map.get(c_def["disease_code"])
                w_obj = ward_map.get(c_def["ward_name"]) or ward_map.get(f"{c_def['district']}:{c_def['ward_name']}")

                if p_obj and d_obj:
                    existing_case = db.query(DiseaseCase).filter(
                        DiseaseCase.patient_id == p_obj.id,
                        DiseaseCase.disease_id == d_obj.id,
                    ).first()
                    
                    diag_date = c_def.get("diagnosis_date") or datetime.date.today()
                    if not existing_case:
                        new_case = DiseaseCase(
                            patient_id=p_obj.id,
                            disease_id=d_obj.id,
                            reported_by_id=officer_user.id if officer_user else None,
                            ward_id=w_obj.id if w_obj else None,
                            case_status=c_def["status"],
                            severity=c_def["severity"],
                            diagnosis_date=diag_date,
                            latitude=c_def["lat"],
                            longitude=c_def["lng"],
                            source="SIMULATED",
                            clinical_notes=c_def["notes"],
                        )
                        db.add(new_case)
                        db.flush()
                        # Set PostGIS Geography Point (Longitude, Latitude) order
                        db.execute(
                            text("UPDATE disease_cases SET location = ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography WHERE id = :id"),
                            {"lng": c_def["lng"], "lat": c_def["lat"], "id": str(new_case.id)},
                        )
                    else:
                        existing_case.latitude = c_def["lat"]
                        existing_case.longitude = c_def["lng"]
                        existing_case.ward_id = w_obj.id if w_obj else existing_case.ward_id
                        existing_case.diagnosis_date = diag_date
                        existing_case.source = "SIMULATED"
                        db.flush()
                        db.execute(
                            text("UPDATE disease_cases SET location = ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography WHERE id = :id"),
                            {"lng": c_def["lng"], "lat": c_def["lat"], "id": str(existing_case.id)},
                        )

            db.commit()
            logger.info("Spatial hierarchy (Districts, LocalBodies, Wards) & Disease Cases initialized with PostGIS geometries.")

            # Seed synthetic movement roadmap route (Points A, B, C, D) for Step 12
            seed_synthetic_roadmap(db)

        finally:
            if close_session:
                db.close()

    except Exception as exc:
        logger.warning(f"init_db notice: {exc}")


def seed_synthetic_roadmap(db: Session):
    """Seed synthetic roadmap route (Points A, B, C, D) for PAT-SYNTH-101 on 2026-09-05."""
    patient = db.query(Patient).filter(Patient.pseudo_id == "PAT-SYNTH-101").first()
    if not patient:
        return

    # Create or reuse consent for 2026-09-05
    now_utc = datetime.datetime(2026, 9, 5, 8, 0, 0, tzinfo=datetime.timezone.utc)
    consent = db.query(LocationConsent).filter(
        LocationConsent.patient_id == patient.id,
        LocationConsent.consent_status == "ACTIVE"
    ).first()
    if not consent:
        consent = LocationConsent(
            patient_id=patient.id,
            consent_status="ACTIVE",
            consent_given_at=now_utc,
            monitoring_start=now_utc,
            monitoring_end=now_utc + datetime.timedelta(days=14),
            purpose="Authorized Movement Roadmap Surveillance (approx. 15 min interval)",
        )
        db.add(consent)
        db.flush()

    # Create or reuse session for 2026-09-05
    session = db.query(MonitoringSession).filter(
        MonitoringSession.patient_id == patient.id,
        MonitoringSession.status == "ACTIVE"
    ).first()
    if not session:
        session = MonitoringSession(
            patient_id=patient.id,
            consent_id=consent.id,
            start_time=now_utc,
            end_time=now_utc + datetime.timedelta(hours=24),
            status="ACTIVE",
        )
        db.add(session)
        db.flush()

    # Define synthetic Points A, B, C, D, E (approx. 15-minute intervals marked source = SIMULATED)
    route_points = [
        {
            "name": "Point A",
            "recorded_at": datetime.datetime(2026, 9, 5, 9, 0, 0, tzinfo=datetime.timezone.utc),
            "lat": 8.5241,
            "lng": 76.9366,
            "acc": 4.2,
            "source": "SIMULATED",
            "obs_id": "SYNTH-ROADMAP-PT-A",
        },
        {
            "name": "Point B",
            "recorded_at": datetime.datetime(2026, 9, 5, 9, 15, 0, tzinfo=datetime.timezone.utc),
            "lat": 8.5305,
            "lng": 76.9420,
            "acc": 5.0,
            "source": "SIMULATED",
            "obs_id": "SYNTH-ROADMAP-PT-B",
        },
        {
            "name": "Point C",
            "recorded_at": datetime.datetime(2026, 9, 5, 9, 30, 0, tzinfo=datetime.timezone.utc),
            "lat": 8.5380,
            "lng": 76.9530,
            "acc": 3.8,
            "source": "SIMULATED",
            "obs_id": "SYNTH-ROADMAP-PT-C",
        },
        {
            "name": "Point D",
            "recorded_at": datetime.datetime(2026, 9, 5, 9, 45, 0, tzinfo=datetime.timezone.utc),
            "lat": 8.5150,
            "lng": 76.9580,
            "acc": 4.5,
            "source": "SIMULATED",
            "obs_id": "SYNTH-ROADMAP-PT-D",
        },
        {
            "name": "Point E",
            "recorded_at": datetime.datetime(2026, 9, 5, 10, 0, 0, tzinfo=datetime.timezone.utc),
            "lat": 8.5080,
            "lng": 76.9620,
            "acc": 6.0,
            "source": "SIMULATED",
            "obs_id": "SYNTH-ROADMAP-PT-E",
        },
    ]

    for pt in route_points:
        existing = db.query(PatientLocation).filter(PatientLocation.client_observation_id == pt["obs_id"]).first()
        if not existing:
            loc = PatientLocation(
                patient_id=patient.id,
                session_id=session.id,
                monitoring_session_id=session.id,
                recorded_at=pt["recorded_at"],
                latitude=pt["lat"],
                longitude=pt["lng"],
                accuracy=pt["acc"],
                accuracy_meters=pt["acc"],
                source=pt["source"],
                client_observation_id=pt["obs_id"],
            )
            db.add(loc)
            db.flush()
            db.execute(
                text("UPDATE patient_locations SET location_geography = ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography WHERE id = :id"),
                {"lng": pt["lng"], "lat": pt["lat"], "id": str(loc.id)},
            )
        else:
            existing.source = pt["source"]
            db.flush()
    db.commit()
    logger.info("Synthetic Movement Roadmap route (Points A, B, C, D, E) seeded for PAT-SYNTH-101.")

    # Seed test patient active consent and monitoring sessions
    seed_test_patient_sessions(db)

    # 13. Seed Synthetic Potential Spatial-Temporal Exposures (Step 16)
    seed_spatial_temporal_exposures(db)


def seed_test_patient_sessions(db: Session) -> None:
    """Ensure personal patient (PAT-USER-143) has active consent and monitoring sessions."""
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    for pseudo in ["PAT-USER-143"]:
        patient = db.query(Patient).filter(Patient.pseudo_id == pseudo).first()
        if not patient:
            continue

        consent = db.query(LocationConsent).filter(LocationConsent.patient_id == patient.id).first()
        if not consent:
            consent = LocationConsent(
                patient_id=patient.id,
                consent_status="ACTIVE",
                consent_given_at=now_utc,
                monitoring_start=now_utc - datetime.timedelta(hours=1),
                monitoring_end=now_utc + datetime.timedelta(days=14),
                purpose="Authorized Quarantine Compliance & Outbreak Contact Surveillance (approx. every 15 mins)",
            )
            db.add(consent)
            db.flush()
        else:
            consent.consent_status = "ACTIVE"
            consent.monitoring_end = now_utc + datetime.timedelta(days=14)
            db.flush()

        session = db.query(MonitoringSession).filter(MonitoringSession.patient_id == patient.id).first()
        if not session:
            session = MonitoringSession(
                patient_id=patient.id,
                consent_id=consent.id,
                start_time=now_utc - datetime.timedelta(hours=1),
                end_time=now_utc + datetime.timedelta(days=14),
                status="ACTIVE",
            )
            db.add(session)
            db.flush()
        else:
            session.status = "ACTIVE"
            session.end_time = now_utc + datetime.timedelta(days=14)
            db.flush()
    db.commit()
    logger.info("Active consent and monitoring sessions verified for test patients PAT-TEST-001 and PAT-USER-143.")


def seed_spatial_temporal_exposures(db: Session) -> None:
    """Seed synthetic location observations and exposure events demonstrating spatial-temporal overlaps."""
    p1 = db.query(Patient).filter(Patient.pseudo_id == "PAT-SYNTH-101").first()
    p2 = db.query(Patient).filter(Patient.pseudo_id == "PAT-SYNTH-102").first()
    officer = db.query(User).filter(User.email == "officer.surveillance@healthwatch.org").first()
    if not p1 or not p2:
        return

    # Ensure Patient 102 has consent and session
    consent2 = db.query(LocationConsent).filter(LocationConsent.patient_id == p2.id).first()
    now_utc = datetime.datetime(2026, 9, 5, 8, 0, 0, tzinfo=datetime.timezone.utc)
    if not consent2:
        consent2 = LocationConsent(
            patient_id=p2.id,
            consent_status="ACTIVE",
            consent_given_at=now_utc,
            monitoring_start=now_utc,
            monitoring_end=now_utc + datetime.timedelta(days=14),
            purpose="Authorized Outbreak Surveillance",
        )
        db.add(consent2)
        db.flush()

    session2 = db.query(MonitoringSession).filter(MonitoringSession.patient_id == p2.id).first()
    if not session2:
        session2 = MonitoringSession(
            patient_id=p2.id,
            consent_id=consent2.id,
            start_time=now_utc,
            end_time=now_utc + datetime.timedelta(hours=24),
            status="ACTIVE",
        )
        db.add(session2)
        db.flush()

    # Seed observations for Patient 102 that overlap in space and time with Patient 101:
    # 1. Near Point A (Palayam): 09:10 UTC (Point A was 09:00 UTC at 8.5241, 76.9366)
    #    lat=8.5243, lng=76.9368 -> distance ~ 30 meters, time_diff = 10 minutes
    # 2. Near Point C (LMS Compound): 09:33 UTC (Point C was 09:30 UTC at 8.5380, 76.9530)
    #    lat=8.5381, lng=76.9531 -> distance ~ 15 meters, time_diff = 3 minutes
    p2_obs = [
        {
            "obs_id": "SYNTH-ROADMAP-P2-A",
            "recorded_at": datetime.datetime(2026, 9, 5, 9, 10, 0, tzinfo=datetime.timezone.utc),
            "lat": 8.5243,
            "lng": 76.9368,
            "acc": 4.0,
        },
        {
            "obs_id": "SYNTH-ROADMAP-P2-C",
            "recorded_at": datetime.datetime(2026, 9, 5, 9, 33, 0, tzinfo=datetime.timezone.utc),
            "lat": 8.5381,
            "lng": 76.9531,
            "acc": 3.5,
        },
    ]

    p2_locations = []
    for obs in p2_obs:
        loc = db.query(PatientLocation).filter(PatientLocation.client_observation_id == obs["obs_id"]).first()
        if not loc:
            loc = PatientLocation(
                patient_id=p2.id,
                session_id=session2.id,
                monitoring_session_id=session2.id,
                recorded_at=obs["recorded_at"],
                latitude=obs["lat"],
                longitude=obs["lng"],
                accuracy=obs["acc"],
                accuracy_meters=obs["acc"],
                source="SIMULATED",
                client_observation_id=obs["obs_id"],
            )
            db.add(loc)
            db.flush()
            db.execute(
                text("UPDATE patient_locations SET location_geography = ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography WHERE id = :id"),
                {"lng": obs["lng"], "lat": obs["lat"], "id": str(loc.id)},
            )
        else:
            loc.source = "SIMULATED"
            db.flush()
        p2_locations.append(loc)

    loc1_a = db.query(PatientLocation).filter(PatientLocation.client_observation_id == "SYNTH-ROADMAP-PT-A").first()
    loc1_c = db.query(PatientLocation).filter(PatientLocation.client_observation_id == "SYNTH-ROADMAP-PT-C").first()

    # Seed demo Exposure Events
    # Event 1: Palayam Market Overlap (POTENTIAL)
    ev1 = db.query(ExposureEvent).filter(
        ExposureEvent.patient_a_id == p1.id,
        ExposureEvent.patient_b_id == p2.id,
        ExposureEvent.status == ExposureStatus.POTENTIAL.value,
    ).first()
    if not ev1:
        ev1 = ExposureEvent(
            patient_a_id=p1.id,
            patient_b_id=p2.id,
            observation_a_id=loc1_a.id if loc1_a else None,
            observation_b_id=p2_locations[0].id if p2_locations else None,
            observation_a_time=datetime.datetime(2026, 9, 5, 9, 0, 0, tzinfo=datetime.timezone.utc),
            observation_b_time=datetime.datetime(2026, 9, 5, 9, 10, 0, tzinfo=datetime.timezone.utc),
            latitude=8.5242,
            longitude=76.9367,
            distance=28.4,
            time_difference=10.0,
            confidence_score=0.82,
            status=ExposureStatus.POTENTIAL.value,
            source_patient_id=p1.id,
            exposed_entity_token="TOKEN-P102-EXPOSURE",
            distance_meters=28.4,
            duration_minutes=10.0,
            risk_score=0.82,
        )
        db.add(ev1)
        db.flush()
        db.execute(
            text("UPDATE exposure_events SET location = ST_SetSRID(ST_MakePoint(76.9367, 8.5242), 4326) WHERE id = :id"),
            {"id": str(ev1.id)},
        )

    # Event 2: LMS Compound Overlap (REVIEWED)
    ev2 = db.query(ExposureEvent).filter(
        ExposureEvent.patient_a_id == p1.id,
        ExposureEvent.patient_b_id == p2.id,
        ExposureEvent.status == ExposureStatus.REVIEWED.value,
    ).first()
    if not ev2:
        ev2 = ExposureEvent(
            patient_a_id=p1.id,
            patient_b_id=p2.id,
            observation_a_id=loc1_c.id if loc1_c else None,
            observation_b_id=p2_locations[1].id if len(p2_locations) > 1 else None,
            observation_a_time=datetime.datetime(2026, 9, 5, 9, 30, 0, tzinfo=datetime.timezone.utc),
            observation_b_time=datetime.datetime(2026, 9, 5, 9, 33, 0, tzinfo=datetime.timezone.utc),
            latitude=8.53805,
            longitude=76.95305,
            distance=14.2,
            time_difference=3.0,
            confidence_score=0.94,
            status=ExposureStatus.REVIEWED.value,
            review_notes="Officer verified spatial corridor proximity at retail pharmacy. Precautionary testing advised.",
            reviewed_by_id=officer.id if officer else None,
            reviewed_at=datetime.datetime(2026, 9, 5, 11, 30, 0, tzinfo=datetime.timezone.utc),
            source_patient_id=p1.id,
            exposed_entity_token="TOKEN-P102-EXPOSURE-LMS",
            distance_meters=14.2,
            duration_minutes=3.0,
            risk_score=0.94,
        )
        db.add(ev2)
        db.flush()
        db.execute(
            text("UPDATE exposure_events SET location = ST_SetSRID(ST_MakePoint(76.95305, 8.53805), 4326) WHERE id = :id"),
            {"id": str(ev2.id)},
        )

    # Event 3: Demo Patients Outbreak Ward Overlap (DISMISSED)
    p_demo1 = db.query(Patient).filter(Patient.pseudo_id == "PAT-DEMO-201").first()
    p_demo2 = db.query(Patient).filter(Patient.pseudo_id == "PAT-DEMO-202").first()
    if p_demo1 and p_demo2:
        ev3 = db.query(ExposureEvent).filter(
            ExposureEvent.patient_a_id == p_demo1.id,
            ExposureEvent.patient_b_id == p_demo2.id,
            ExposureEvent.status == ExposureStatus.DISMISSED.value,
        ).first()
        if not ev3:
            ev3 = ExposureEvent(
                patient_a_id=p_demo1.id,
                patient_b_id=p_demo2.id,
                latitude=8.5020,
                longitude=76.9510,
                distance=44.0,
                time_difference=12.0,
                confidence_score=0.52,
                status=ExposureStatus.DISMISSED.value,
                review_notes="Dismissed by officer: Architectural barrier separates the patients (separate hospital wings).",
                reviewed_by_id=officer.id if officer else None,
                reviewed_at=datetime.datetime(2026, 9, 5, 12, 0, 0, tzinfo=datetime.timezone.utc),
                source_patient_id=p_demo1.id,
                exposed_entity_token="TOKEN-DEMO-DISMISSED",
                distance_meters=44.0,
                duration_minutes=12.0,
                risk_score=0.52,
            )
            db.add(ev3)
            db.flush()
            db.execute(
                text("UPDATE exposure_events SET location = ST_SetSRID(ST_MakePoint(76.9510, 8.5020), 4326) WHERE id = :id"),
                {"id": str(ev3.id)},
            )

    db.commit()
    logger.info("Step 16 synthetic spatial-temporal exposure data and candidate overlaps seeded successfully.")

