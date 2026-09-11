package com.healthwatch.data.local;

import android.content.ContentValues;
import android.content.Context;
import android.database.Cursor;
import android.database.sqlite.SQLiteDatabase;
import android.database.sqlite.SQLiteOpenHelper;
import com.healthwatch.data.model.LocationModels.QueuedLocationObservation;
import java.util.ArrayList;
import java.util.List;

public class OfflineLocationQueue extends SQLiteOpenHelper {

    private static final String DATABASE_NAME = "healthwatch_offline_queue.db";
    private static final int DATABASE_VERSION = 1;

    private static final String TABLE_NAME = "queued_observations";
    private static final String COL_LOCAL_ID = "local_id";
    private static final String COL_PATIENT_ID = "patient_id";
    private static final String COL_SESSION_ID = "session_id";
    private static final String COL_LATITUDE = "latitude";
    private static final String COL_LONGITUDE = "longitude";
    private static final String COL_ACCURACY = "accuracy";
    private static final String COL_RECORDED_AT = "recorded_at";
    private static final String COL_SOURCE = "source";
    private static final String COL_SYNC_STATUS = "sync_status";
    private static final String COL_RETRY_COUNT = "retry_count";
    private static final String COL_CREATED_AT = "created_at";

    public OfflineLocationQueue(Context context) {
        super(context, DATABASE_NAME, null, DATABASE_VERSION);
    }

    @Override
    public void onCreate(SQLiteDatabase db) {
        String createTableQuery = "CREATE TABLE " + TABLE_NAME + " ("
                + COL_LOCAL_ID + " INTEGER PRIMARY KEY AUTOINCREMENT, "
                + COL_PATIENT_ID + " TEXT NOT NULL, "
                + COL_SESSION_ID + " TEXT NOT NULL, "
                + COL_LATITUDE + " REAL NOT NULL, "
                + COL_LONGITUDE + " REAL NOT NULL, "
                + COL_ACCURACY + " REAL, "
                + COL_RECORDED_AT + " TEXT NOT NULL, "
                + COL_SOURCE + " TEXT DEFAULT 'PATIENT_GPS', "
                + COL_SYNC_STATUS + " TEXT DEFAULT 'PENDING', "
                + COL_RETRY_COUNT + " INTEGER DEFAULT 0, "
                + COL_CREATED_AT + " INTEGER NOT NULL"
                + ")";
        db.execSQL(createTableQuery);
    }

    @Override
    public void onUpgrade(SQLiteDatabase db, int oldVersion, int newVersion) {
        db.execSQL("DROP TABLE IF EXISTS " + TABLE_NAME);
        onCreate(db);
    }

    public long enqueueObservation(QueuedLocationObservation obs) {
        SQLiteDatabase db = getWritableDatabase();
        ContentValues values = new ContentValues();
        values.put(COL_PATIENT_ID, obs.getPatientId());
        values.put(COL_SESSION_ID, obs.getMonitoringSessionId());
        values.put(COL_LATITUDE, obs.getLatitude());
        values.put(COL_LONGITUDE, obs.getLongitude());
        values.put(COL_ACCURACY, obs.getAccuracy());
        values.put(COL_RECORDED_AT, obs.getRecordedAt());
        values.put(COL_SOURCE, obs.getSource());
        values.put(COL_SYNC_STATUS, "PENDING");
        values.put(COL_RETRY_COUNT, 0);
        values.put(COL_CREATED_AT, System.currentTimeMillis());
        return db.insert(TABLE_NAME, null, values);
    }

    public List<QueuedLocationObservation> getPendingObservations(int limit) {
        List<QueuedLocationObservation> list = new ArrayList<>();
        SQLiteDatabase db = getReadableDatabase();
        Cursor cursor = db.query(
                TABLE_NAME,
                null,
                COL_SYNC_STATUS + " = ?",
                new String[]{"PENDING"},
                null,
                null,
                COL_CREATED_AT + " ASC",
                String.valueOf(limit)
        );

        if (cursor != null) {
            try {
                int colLocalId = cursor.getColumnIndexOrThrow(COL_LOCAL_ID);
                int colPatientId = cursor.getColumnIndexOrThrow(COL_PATIENT_ID);
                int colSessionId = cursor.getColumnIndexOrThrow(COL_SESSION_ID);
                int colLat = cursor.getColumnIndexOrThrow(COL_LATITUDE);
                int colLng = cursor.getColumnIndexOrThrow(COL_LONGITUDE);
                int colAcc = cursor.getColumnIndexOrThrow(COL_ACCURACY);
                int colRec = cursor.getColumnIndexOrThrow(COL_RECORDED_AT);
                int colSrc = cursor.getColumnIndexOrThrow(COL_SOURCE);
                int colSync = cursor.getColumnIndexOrThrow(COL_SYNC_STATUS);
                int colRetry = cursor.getColumnIndexOrThrow(COL_RETRY_COUNT);
                int colCreated = cursor.getColumnIndexOrThrow(COL_CREATED_AT);

                while (cursor.moveToNext()) {
                    Float acc = cursor.isNull(colAcc) ? null : cursor.getFloat(colAcc);
                    QueuedLocationObservation obs = new QueuedLocationObservation(
                            cursor.getLong(colLocalId),
                            cursor.getString(colPatientId),
                            cursor.getString(colSessionId),
                            cursor.getDouble(colLat),
                            cursor.getDouble(colLng),
                            acc,
                            cursor.getString(colRec),
                            cursor.getString(colSrc),
                            cursor.getString(colSync),
                            cursor.getInt(colRetry),
                            cursor.getLong(colCreated)
                    );
                    list.add(obs);
                }
            } finally {
                cursor.close();
            }
        }
        return list;
    }

    public void markSynced(long localId) {
        SQLiteDatabase db = getWritableDatabase();
        ContentValues values = new ContentValues();
        values.put(COL_SYNC_STATUS, "SYNCED");
        db.update(TABLE_NAME, values, COL_LOCAL_ID + " = ?", new String[]{String.valueOf(localId)});
    }

    public void markFailed(long localId) {
        SQLiteDatabase db = getWritableDatabase();
        db.execSQL("UPDATE " + TABLE_NAME + " SET " + COL_RETRY_COUNT + " = " + COL_RETRY_COUNT + " + 1 WHERE " + COL_LOCAL_ID + " = " + localId);
    }

    public List<QueuedLocationObservation> getAllObservations(int limit) {
        List<QueuedLocationObservation> list = new ArrayList<>();
        SQLiteDatabase db = getReadableDatabase();
        Cursor cursor = db.query(
                TABLE_NAME,
                null,
                null,
                null,
                null,
                null,
                COL_CREATED_AT + " DESC",
                String.valueOf(limit)
        );

        if (cursor != null) {
            try {
                int colLocalId = cursor.getColumnIndexOrThrow(COL_LOCAL_ID);
                int colPatientId = cursor.getColumnIndexOrThrow(COL_PATIENT_ID);
                int colSessionId = cursor.getColumnIndexOrThrow(COL_SESSION_ID);
                int colLat = cursor.getColumnIndexOrThrow(COL_LATITUDE);
                int colLng = cursor.getColumnIndexOrThrow(COL_LONGITUDE);
                int colAcc = cursor.getColumnIndexOrThrow(COL_ACCURACY);
                int colRec = cursor.getColumnIndexOrThrow(COL_RECORDED_AT);
                int colSrc = cursor.getColumnIndexOrThrow(COL_SOURCE);
                int colSync = cursor.getColumnIndexOrThrow(COL_SYNC_STATUS);
                int colRetry = cursor.getColumnIndexOrThrow(COL_RETRY_COUNT);
                int colCreated = cursor.getColumnIndexOrThrow(COL_CREATED_AT);

                while (cursor.moveToNext()) {
                    Float acc = cursor.isNull(colAcc) ? null : cursor.getFloat(colAcc);
                    QueuedLocationObservation obs = new QueuedLocationObservation(
                            cursor.getLong(colLocalId),
                            cursor.getString(colPatientId),
                            cursor.getString(colSessionId),
                            cursor.getDouble(colLat),
                            cursor.getDouble(colLng),
                            acc,
                            cursor.getString(colRec),
                            cursor.getString(colSrc),
                            cursor.getString(colSync),
                            cursor.getInt(colRetry),
                            cursor.getLong(colCreated)
                    );
                    list.add(obs);
                }
            } finally {
                cursor.close();
            }
        }
        return list;
    }

    public int getPendingCount() {
        SQLiteDatabase db = getReadableDatabase();
        Cursor cursor = db.rawQuery("SELECT COUNT(*) FROM " + TABLE_NAME + " WHERE " + COL_SYNC_STATUS + " = 'PENDING'", null);
        if (cursor != null) {
            try {
                if (cursor.moveToFirst()) {
                    return cursor.getInt(0);
                }
            } finally {
                cursor.close();
            }
        }
        return 0;
    }
}
