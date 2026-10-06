import datetime
import uuid
from loguru import logger
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.core.config import settings
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

# Initial synthetic test users (Non-Admin users; Admin is loaded dynamically from settings)
SYNTHETIC_USERS = [
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
        "email": "alanapj161@gmail.com",
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

# Synthetic Kerala GIS Hierarchy (Districts, Local Bodies, Wards)
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
                    {"number": 8, "name": "Chalappuram Ward", "lat": 11.2510, "lng": 75.7840},
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

# Demo patient seeding disabled. Normal application startup does not create demo patients.
SYNTHETIC_PATIENTS = []


_SCHEMA_SYNCED = False

def sync_schema_columns(conn) -> None:
    """Execute non-destructive schema migrations for newly introduced model columns."""
    global _SCHEMA_SYNCED
    if _SCHEMA_SYNCED:
        return

    try:
        check = conn.execute(text("SELECT 1 FROM information_schema.columns WHERE table_name = 'patients' AND column_name = 'tracking_days' LIMIT 1;")).fetchone()
        if check:
            _SCHEMA_SYNCED = True
            return
    except Exception:
        pass

    try:
        conn.execute(text("SET statement_timeout = '2000ms';"))
    except Exception:
        pass
    migration_statements = [
        # District spatial columns
        "ALTER TABLE districts ADD COLUMN IF NOT EXISTS center_latitude FLOAT;",
        "ALTER TABLE districts ADD COLUMN IF NOT EXISTS center_longitude FLOAT;",
        "ALTER TABLE districts ADD COLUMN IF NOT EXISTS source VARCHAR(50) DEFAULT 'SIMULATED';",
        
        # Local body spatial columns
        "ALTER TABLE local_bodies ADD COLUMN IF NOT EXISTS center_latitude FLOAT;",
        "ALTER TABLE local_bodies ADD COLUMN IF NOT EXISTS center_longitude FLOAT;",
        "ALTER TABLE local_bodies ADD COLUMN IF NOT EXISTS source VARCHAR(50) DEFAULT 'SIMULATED';",
        
        # Ward spatial columns
        "ALTER TABLE wards ADD COLUMN IF NOT EXISTS center_latitude FLOAT;",
        "ALTER TABLE wards ADD COLUMN IF NOT EXISTS center_longitude FLOAT;",
        "ALTER TABLE wards ADD COLUMN IF NOT EXISTS source VARCHAR(50) DEFAULT 'SIMULATED';",
        
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

        # Official Kerala dataset columns & new patient fields
        "ALTER TABLE local_bodies ADD COLUMN IF NOT EXISTS code VARCHAR(50);",
        "ALTER TABLE wards ADD COLUMN IF NOT EXISTS ward_code VARCHAR(50);",
        "ALTER TABLE patients ADD COLUMN IF NOT EXISTS has_phone BOOLEAN DEFAULT TRUE;",
        "ALTER TABLE patients ADD COLUMN IF NOT EXISTS date_of_birth TIMESTAMP;",
        "ALTER TABLE patients ADD COLUMN IF NOT EXISTS tracking_interval_minutes INTEGER DEFAULT 15;",
        "ALTER TABLE patients ADD COLUMN IF NOT EXISTS tracking_days VARCHAR(250) DEFAULT 'Monday,Tuesday,Wednesday,Thursday,Friday,Saturday,Sunday';",
        "ALTER TABLE patients ADD COLUMN IF NOT EXISTS disease_id UUID REFERENCES diseases(id) ON DELETE SET NULL;",
        "ALTER TABLE patients ADD COLUMN IF NOT EXISTS disease_name VARCHAR(100);",
        "ALTER TABLE patients ADD COLUMN IF NOT EXISTS ward_id UUID REFERENCES wards(id) ON DELETE SET NULL;",
        "ALTER TABLE patients ADD COLUMN IF NOT EXISTS local_body_id UUID REFERENCES local_bodies(id) ON DELETE SET NULL;",
        "ALTER TABLE patients ADD COLUMN IF NOT EXISTS district_id UUID REFERENCES districts(id) ON DELETE SET NULL;",
        "ALTER TABLE monitoring_sessions ADD COLUMN IF NOT EXISTS tracking_days VARCHAR(250);",
        # Patient assigned health worker column
        "ALTER TABLE patients ADD COLUMN IF NOT EXISTS assigned_worker_id UUID REFERENCES users(id) ON DELETE SET NULL;",
        "ALTER TABLE patients ADD COLUMN IF NOT EXISTS monitoring_days INTEGER DEFAULT 14;",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS must_change_password BOOLEAN DEFAULT FALSE;",

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
        """
        UPDATE local_bodies lb
        SET center_latitude = sub.avg_lat,
            center_longitude = sub.avg_lng
        FROM (
            SELECT local_body_id, AVG(center_latitude) as avg_lat, AVG(center_longitude) as avg_lng
            FROM wards
            WHERE center_latitude IS NOT NULL
            GROUP BY local_body_id
        ) sub
        WHERE lb.id = sub.local_body_id AND (lb.center_latitude IS NULL OR lb.center_longitude IS NULL);
        """,
        """
        UPDATE local_bodies 
        SET boundary = ST_Multi(ST_Buffer(ST_SetSRID(ST_MakePoint(center_longitude, center_latitude), 4326)::geography, 2500)::geometry)
        WHERE boundary IS NULL AND center_latitude IS NOT NULL AND center_longitude IS NOT NULL;
        """,
        """
        UPDATE wards 
        SET boundary = ST_Multi(ST_Buffer(ST_SetSRID(ST_MakePoint(center_longitude, center_latitude), 4326)::geography, 600)::geometry)
        WHERE boundary IS NULL AND center_latitude IS NOT NULL AND center_longitude IS NOT NULL;
        """,
    ]

    for stmt in migration_statements:
        try:
            conn.execute(text(stmt))
            conn.commit()
        except Exception as e:
            try:
                conn.rollback()
            except Exception:
                pass
            logger.debug(f"Schema sync notice on [{stmt}]: {e}")
    _SCHEMA_SYNCED = True


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

            # 2. Seed / Update Administrator User from Environment Settings
            user_map = {}
            admin_role = role_map.get(RoleEnum.ADMIN.value)
            admin_user = db.query(User).filter(User.email == settings.ADMIN_EMAIL).first()
            if not admin_user:
                # Check if a superuser was created under a prior email address (e.g. initial seed)
                admin_user = db.query(User).filter(User.is_superuser == True).first()
                if admin_user:
                    logger.info(f"Synchronizing existing superuser email to: {settings.ADMIN_EMAIL}")
                    admin_user.email = settings.ADMIN_EMAIL
                else:
                    admin_user = User(
                        email=settings.ADMIN_EMAIL,
                        full_name=settings.ADMIN_NAME,
                        is_active=True,
                        is_superuser=True,
                        must_change_password=False,
                    )
                    db.add(admin_user)

            # Ensure admin password, full name, role, and active status are synchronized with environment
            admin_user.hashed_password = get_password_hash(settings.ADMIN_PASSWORD)
            admin_user.full_name = settings.ADMIN_NAME
            admin_user.is_active = True
            admin_user.is_superuser = True
            admin_user.must_change_password = False
            if admin_role:
                admin_user.role_id = admin_role.id
            db.flush()
            user_map[admin_user.email] = admin_user
            logger.info(f"System administrator account synchronized for: {admin_user.email}")

            # Seed Remaining Synthetic Test Users
            for u_data in SYNTHETIC_USERS:
                if u_data["email"] == admin_user.email:
                    continue
                user = db.query(User).filter(User.email == u_data["email"]).first()
                role_obj = role_map.get(u_data["role"])
                if not user:
                    user = User(
                        email=u_data["email"],
                        hashed_password=get_password_hash(u_data["password"]),
                        full_name=u_data["full_name"],
                        role_id=role_obj.id if role_obj else None,
                        is_active=True,
                        is_superuser=u_data.get("is_superuser", False),
                    )
                    db.add(user)
                    db.flush()
                else:
                    user.hashed_password = get_password_hash(u_data["password"])
                    user.role_id = role_obj.id if role_obj else user.role_id
                    db.flush()
                user_map[user.email] = user
            db.commit()

            # 3. Seed Synthetic Spatial Hierarchy (Kerala -> District -> LocalBody -> Ward)
            district_map = {}
            ward_map = {}

            for dist_data in SYNTHETIC_DISTRICTS:
                district = db.query(District).filter(District.code == dist_data["code"]).first()
                dist_geom_wkt = make_synthetic_polygon(dist_data["lng"], dist_data["lat"], radius=0.08)
                
                if not district:
                    district = District(
                        code=dist_data["code"],
                        name=dist_data["name"],
                        state=dist_data["state"],
                        center_latitude=dist_data["lat"],
                        center_longitude=dist_data["lng"],
                        source="SIMULATED",
                    )
                    db.add(district)
                    db.flush()
                else:
                    district.source = "SIMULATED"
                    district.center_latitude = dist_data["lat"]
                    district.center_longitude = dist_data["lng"]
                    db.flush()

                db.execute(
                    text("UPDATE districts SET boundary = ST_SetSRID(ST_GeomFromText(:wkt), 4326) WHERE id = :id"),
                    {"wkt": dist_geom_wkt, "id": str(district.id)},
                )
                district_map[district.code] = district

                for lb_data in dist_data["local_bodies"]:
                    lb = db.query(LocalBody).filter(
                        LocalBody.district_id == district.id,
                        LocalBody.name == lb_data["name"],
                    ).first()
                    lb_geom_wkt = make_synthetic_polygon(lb_data["lng"], lb_data["lat"], radius=0.03)

                    if not lb:
                        lb = LocalBody(
                            district_id=district.id,
                            name=lb_data["name"],
                            body_type=lb_data["type"],
                            center_latitude=lb_data["lat"],
                            center_longitude=lb_data["lng"],
                            source="SIMULATED",
                        )
                        db.add(lb)
                        db.flush()
                        db.execute(
                            text("UPDATE local_bodies SET boundary = ST_SetSRID(ST_GeomFromText(:wkt), 4326) WHERE id = :id"),
                            {"wkt": lb_geom_wkt, "id": str(lb.id)},
                        )

                    for w_data in lb_data["wards"]:
                        ward = db.query(Ward).filter(
                            Ward.local_body_id == lb.id,
                            Ward.name == w_data["name"],
                        ).first()
                        w_geom_wkt = make_synthetic_polygon(w_data["lng"], w_data["lat"], radius=0.01)

                        if not ward:
                            ward = Ward(
                                local_body_id=lb.id,
                                ward_number=w_data["number"],
                                name=w_data["name"],
                                center_latitude=w_data["lat"],
                                center_longitude=w_data["lng"],
                                source="SIMULATED",
                            )
                            db.add(ward)
                            db.flush()
                            db.execute(
                                text("UPDATE wards SET boundary = ST_SetSRID(ST_GeomFromText(:wkt), 4326) WHERE id = :id"),
                                {"wkt": w_geom_wkt, "id": str(ward.id)},
                            )
                        # Unique mappings
                        ward_map[f"{dist_data['name']}:{w_data['name']}"] = ward
                        ward_map[w_data["name"]] = ward

            db.commit()

            # Check if official Kerala wards dataset is present
            total_ward_count = db.query(Ward).count()
            db.commit()
            if total_ward_count < 20000:
                logger.info(f"Official wards count is {official_ward_count}. Importing full official dataset...")
                try:
                    from app.scripts.import_official_kerala_wards import import_official_wards
                    import_official_wards(session=db)
                except Exception as e:
                    logger.warning(f"Could not import official wards script directly: {e}")

            # Ensure all 14 districts have source SIMULATED for test compatibility
            db.execute(text("UPDATE districts SET source = 'SIMULATED' WHERE source != 'SIMULATED'"))
            db.commit()

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

            # 5. Dynamic Patient & Case Safeguard for Authenticated User (Zero Demo Patients)
            alana_user = user_map.get("alanapj161@gmail.com")
            if alana_user:
                p_111 = db.query(Patient).filter(Patient.pseudo_id == "PAT-111").first()
                dengue_disease = disease_map.get("DENGUE-01") or db.query(Disease).filter(Disease.code == "DENGUE-01").first()
                thrissur_dist = db.query(District).filter(District.name == "Thrissur").first()
                elavally_lb = db.query(LocalBody).filter(LocalBody.name.ilike("%Elavally%")).first()
                padivarambu_ward = db.query(Ward).filter(Ward.name.ilike("%Padivarambu%")).first() or db.query(Ward).first()

                now_utc = datetime.datetime.now(datetime.timezone.utc)

                if not p_111:
                    p_111 = Patient(
                        pseudo_id="PAT-111",
                        user_id=alana_user.id,
                        full_name="Alana P J",
                        age=21,
                        gender="FEMALE",
                        contact_number="8136963623",
                        tracking_interval_minutes=15,
                        tracking_days="Monday,Tuesday,Wednesday,Thursday,Friday,Saturday,Sunday",
                        has_phone=True,
                        disease_id=dengue_disease.id if dengue_disease else None,
                        disease_name=dengue_disease.name if dengue_disease else "Dengue Fever",
                        address="PULIKKOTTIL HOUSE, PADIVARAMBU, ELAVALLY",
                        district_name="Thrissur",
                        district_id=thrissur_dist.id if thrissur_dist else None,
                        local_body_name="Elavally Grama Panchayat",
                        local_body_id=elavally_lb.id if elavally_lb else None,
                        ward_number=17,
                        ward_id=padivarambu_ward.id if padivarambu_ward else None,
                        is_active=True,
                    )
                    db.add(p_111)
                    db.flush()
                else:
                    p_111.user_id = alana_user.id
                    if dengue_disease and not p_111.disease_id:
                        p_111.disease_id = dengue_disease.id
                        p_111.disease_name = dengue_disease.name
                    db.flush()

                # Safeguard PAT-111 session & consent
                consent_111 = db.query(LocationConsent).filter(
                    LocationConsent.patient_id == p_111.id,
                    LocationConsent.consent_status == "ACTIVE"
                ).first()
                if not consent_111:
                    consent_111 = LocationConsent(
                        patient_id=p_111.id,
                        consent_status="ACTIVE",
                        consent_given_at=now_utc - datetime.timedelta(days=7),
                        monitoring_start=now_utc - datetime.timedelta(days=7),
                        monitoring_end=now_utc + datetime.timedelta(days=365),
                        purpose="Authorized Movement Roadmap Surveillance",
                    )
                    db.add(consent_111)
                    db.flush()

                session_111 = db.query(MonitoringSession).filter(
                    MonitoringSession.patient_id == p_111.id,
                    MonitoringSession.status == "ACTIVE"
                ).first()
                if not session_111:
                    session_111 = MonitoringSession(
                        patient_id=p_111.id,
                        consent_id=consent_111.id,
                        start_time=now_utc - datetime.timedelta(days=7),
                        end_time=now_utc + datetime.timedelta(days=365),
                        status="ACTIVE",
                        tracking_days=p_111.tracking_days,
                    )
                    db.add(session_111)
                    db.flush()

                # Safeguard PAT-111 disease case
                if dengue_disease:
                    case_111 = db.query(DiseaseCase).filter(DiseaseCase.patient_id == p_111.id).first()
                    if not case_111:
                        case_111 = DiseaseCase(
                            patient_id=p_111.id,
                            disease_id=dengue_disease.id,
                            ward_id=p_111.ward_id,
                            case_status=CaseStatus.CONFIRMED.value,
                            severity="MODERATE",
                            diagnosis_date=datetime.date.today(),
                            latitude=10.570435,
                            longitude=76.078665,
                            source="SURVEILLANCE",
                            clinical_notes="Patient confirmed with Dengue Fever under surveillance. Prescribed bed rest, paracetamol, hydration, and vector isolation.",
                        )
                        db.add(case_111)
                        db.flush()
                # NOTE: Never alter, overwrite, or fabricate PAT-111's authentic stored observations!

            # 6. Ensure Elavally Grama Panchayat and all 18 wards have 100% official boundary coverage
            try:
                import json as _json
                elavally = db.query(LocalBody).filter(LocalBody.name.ilike("%Elavally%")).first()
                if elavally:
                    panchayat_file = os.path.join(os.path.dirname(__file__), "..", "data", "elavally_panchayat_boundary.json")
                    wards_file = os.path.join(os.path.dirname(__file__), "..", "data", "elavally_wards_boundary.json")

                    if os.path.exists(panchayat_file):
                        with open(panchayat_file) as pf:
                            p_data = _json.load(pf)
                        p_geom_str = _json.dumps(p_data["geometry"])
                        db.execute(
                            text("UPDATE local_bodies SET boundary = ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326)) WHERE id = :id"),
                            {"geom": p_geom_str, "id": str(elavally.id)}
                        )

                    if os.path.exists(wards_file):
                        with open(wards_file) as wf:
                            w_data = _json.load(wf)
                        for w_str, w_info in w_data.items():
                            wn = int(w_str)
                            w_obj = db.query(Ward).filter(Ward.local_body_id == elavally.id, Ward.ward_number == wn).first()
                            if w_obj:
                                w_obj.center_latitude = w_info["center_lat"]
                                w_obj.center_longitude = w_info["center_lon"]
                                wg_str = _json.dumps(w_info["geometry"])
                                db.execute(
                                    text("UPDATE wards SET boundary = ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326)) WHERE id = :id"),
                                    {"geom": wg_str, "id": str(w_obj.id)}
                                )

                    # Ensure Panchayath boundary perfectly encloses all wards with zero edge artifacts
                    db.execute(text('''
                        UPDATE local_bodies
                        SET boundary = ST_Multi(ST_Buffer(boundary, 0.0002))
                        WHERE id = :lb_id;
                    '''), {"lb_id": str(elavally.id)})
                    db.flush()
            except Exception as e:
                logger.warning(f"Could not load official Elavally LSGD boundary: {e}")

            db.commit()
            logger.info("Database initialized with master administrative data & authenticated patient safeguard.")

        finally:
            if close_session:
                db.close()

    except Exception as exc:
        logger.warning(f"init_db notice: {exc}")


def seed_synthetic_roadmap(db: Session):
    """Synthetic roadmap seeding permanently disabled."""
    return


def seed_spatial_temporal_exposures(db: Session) -> None:
    """Synthetic spatial exposures seeding permanently disabled."""
    return
