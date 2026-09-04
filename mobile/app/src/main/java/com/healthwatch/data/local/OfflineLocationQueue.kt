package com.healthwatch.data.local

import android.content.ContentValues
import android.content.Context
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper
import com.healthwatch.data.model.QueuedLocationObservation

/**
 * Local temporary offline queue for GPS observations.
 * Persists observations to SQLite when network connectivity is lost.
 * Automatically flushes upon network reconnection to avoid data loss.
 */
class OfflineLocationQueue(context: Context) : SQLiteOpenHelper(context, DATABASE_NAME, null, DATABASE_VERSION) {

    companion object {
        private const val DATABASE_NAME = "healthwatch_offline_queue.db"
        private const val DATABASE_VERSION = 1

        private const val TABLE_NAME = "queued_observations"
        private const val COL_LOCAL_ID = "local_id"
        private const val COL_PATIENT_ID = "patient_id"
        private const val COL_SESSION_ID = "session_id"
        private const val COL_LATITUDE = "latitude"
        private const val COL_LONGITUDE = "longitude"
        private const val COL_ACCURACY = "accuracy"
        private const val COL_RECORDED_AT = "recorded_at"
        private const val COL_SOURCE = "source"
        private const val COL_SYNC_STATUS = "sync_status"
        private const val COL_RETRY_COUNT = "retry_count"
        private const val COL_CREATED_AT = "created_at"
    }

    override fun onCreate(db: SQLiteDatabase) {
        val createTableQuery = """
            CREATE TABLE $TABLE_NAME (
                $COL_LOCAL_ID INTEGER PRIMARY KEY AUTOINCREMENT,
                $COL_PATIENT_ID TEXT NOT NULL,
                $COL_SESSION_ID TEXT NOT NULL,
                $COL_LATITUDE REAL NOT NULL,
                $COL_LONGITUDE REAL NOT NULL,
                $COL_ACCURACY REAL,
                $COL_RECORDED_AT TEXT NOT NULL,
                $COL_SOURCE TEXT DEFAULT 'PATIENT_GPS',
                $COL_SYNC_STATUS TEXT DEFAULT 'PENDING',
                $COL_RETRY_COUNT INTEGER DEFAULT 0,
                $COL_CREATED_AT INTEGER NOT NULL
            )
        """.trimIndent()
        db.execSQL(createTableQuery)
    }

    override fun onUpgrade(db: SQLiteDatabase, oldVersion: Int, newVersion: Int) {
        db.execSQL("DROP TABLE IF EXISTS $TABLE_NAME")
        onCreate(db)
    }

    /**
     * Enqueue observation locally when offline or network fails.
     */
    fun enqueueObservation(obs: QueuedLocationObservation): Long {
        val db = writableDatabase
        val values = ContentValues().apply {
            put(COL_PATIENT_ID, obs.patientId)
            put(COL_SESSION_ID, obs.monitoringSessionId)
            put(COL_LATITUDE, obs.latitude)
            put(COL_LONGITUDE, obs.longitude)
            put(COL_ACCURACY, obs.accuracy)
            put(COL_RECORDED_AT, obs.recordedAt)
            put(COL_SOURCE, obs.source)
            put(COL_SYNC_STATUS, "PENDING")
            put(COL_RETRY_COUNT, 0)
            put(COL_CREATED_AT, System.currentTimeMillis())
        }
        return db.insert(TABLE_NAME, null, values)
    }

    /**
     * Retrieve observations pending upload to backend.
     */
    fun getPendingObservations(limit: Int = 50): List<QueuedLocationObservation> {
        val list = mutableListOf<QueuedLocationObservation>()
        val db = readableDatabase
        val cursor = db.query(
            TABLE_NAME,
            null,
            "$COL_SYNC_STATUS = ?",
            arrayOf("PENDING"),
            null,
            null,
            "$COL_CREATED_AT ASC",
            limit.toString()
        )

        cursor.use {
            while (it.moveToNext()) {
                list.add(
                    QueuedLocationObservation(
                        localId = it.getLong(it.getColumnIndexOrThrow(COL_LOCAL_ID)),
                        patientId = it.getString(it.getColumnIndexOrThrow(COL_PATIENT_ID)),
                        monitoringSessionId = it.getString(it.getColumnIndexOrThrow(COL_SESSION_ID)),
                        latitude = it.getDouble(it.getColumnIndexOrThrow(COL_LATITUDE)),
                        longitude = it.getDouble(it.getColumnIndexOrThrow(COL_LONGITUDE)),
                        accuracy = if (it.isNull(it.getColumnIndexOrThrow(COL_ACCURACY))) null else it.getFloat(it.getColumnIndexOrThrow(COL_ACCURACY)),
                        recordedAt = it.getString(it.getColumnIndexOrThrow(COL_RECORDED_AT)),
                        source = it.getString(it.getColumnIndexOrThrow(COL_SOURCE)),
                        syncStatus = it.getString(it.getColumnIndexOrThrow(COL_SYNC_STATUS)),
                        retryCount = it.getInt(it.getColumnIndexOrThrow(COL_RETRY_COUNT)),
                        createdAt = it.getLong(it.getColumnIndexOrThrow(COL_CREATED_AT))
                    )
                )
            }
        }
        return list
    }

    /**
     * Mark observation as successfully synced with the server.
     */
    fun markSynced(localId: Long) {
        val db = writableDatabase
        val values = ContentValues().apply {
            put(COL_SYNC_STATUS, "SYNCED")
        }
        db.update(TABLE_NAME, values, "$COL_LOCAL_ID = ?", arrayOf(localId.toString()))
    }

    /**
     * Mark observation as failed with incremented retry count.
     */
    fun markFailed(localId: Long) {
        val db = writableDatabase
        db.execSQL("UPDATE $TABLE_NAME SET $COL_RETRY_COUNT = $COL_RETRY_COUNT + 1 WHERE $COL_LOCAL_ID = $localId")
    }

    /**
     * Retrieve all observations (synced + pending) for Location History screen.
     */
    fun getAllObservations(limit: Int = 100): List<QueuedLocationObservation> {
        val list = mutableListOf<QueuedLocationObservation>()
        val db = readableDatabase
        val cursor = db.query(
            TABLE_NAME,
            null,
            null,
            null,
            null,
            null,
            "$COL_CREATED_AT DESC",
            limit.toString()
        )

        cursor.use {
            while (it.moveToNext()) {
                list.add(
                    QueuedLocationObservation(
                        localId = it.getLong(it.getColumnIndexOrThrow(COL_LOCAL_ID)),
                        patientId = it.getString(it.getColumnIndexOrThrow(COL_PATIENT_ID)),
                        monitoringSessionId = it.getString(it.getColumnIndexOrThrow(COL_SESSION_ID)),
                        latitude = it.getDouble(it.getColumnIndexOrThrow(COL_LATITUDE)),
                        longitude = it.getDouble(it.getColumnIndexOrThrow(COL_LONGITUDE)),
                        accuracy = if (it.isNull(it.getColumnIndexOrThrow(COL_ACCURACY))) null else it.getFloat(it.getColumnIndexOrThrow(COL_ACCURACY)),
                        recordedAt = it.getString(it.getColumnIndexOrThrow(COL_RECORDED_AT)),
                        source = it.getString(it.getColumnIndexOrThrow(COL_SOURCE)),
                        syncStatus = it.getString(it.getColumnIndexOrThrow(COL_SYNC_STATUS)),
                        retryCount = it.getInt(it.getColumnIndexOrThrow(COL_RETRY_COUNT)),
                        createdAt = it.getLong(it.getColumnIndexOrThrow(COL_CREATED_AT))
                    )
                )
            }
        }
        return list
    }

    /**
     * Count pending offline observations.
     */
    fun getPendingCount(): Int {
        val db = readableDatabase
        val cursor = db.rawQuery("SELECT COUNT(*) FROM $TABLE_NAME WHERE $COL_SYNC_STATUS = 'PENDING'", null)
        cursor.use {
            if (it.moveToFirst()) {
                return it.getInt(0)
            }
        }
        return 0
    }
}
