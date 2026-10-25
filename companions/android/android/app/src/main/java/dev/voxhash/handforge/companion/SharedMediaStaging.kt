package dev.voxhash.handforge.companion

import android.content.ContentValues
import android.content.Context
import android.net.Uri
import android.os.Build
import android.os.Environment
import android.provider.MediaStore
import java.io.File
import java.io.FileOutputStream

/**
 * Stages picked SAF content into shared Download/HandForge so Termux can read/write paths.
 */
object SharedMediaStaging {

    const val RELATIVE_DIR = "Download/HandForge"
    const val PUBLIC_DIR_NAME = "HandForge"

    data class StagedPaths(
        val inputAbsPath: String,
        val outputAbsPath: String,
        val workDir: String,
    )

    fun publicWorkDir(): File {
        val downloads = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS)
        val dir = File(downloads, PUBLIC_DIR_NAME)
        if (!dir.exists()) {
            dir.mkdirs()
        }
        return dir
    }

    fun absoluteUnderDownloads(fileName: String): String {
        return File(publicWorkDir(), fileName).absolutePath
    }

    /**
     * Copy [source] into Download/HandForge/[inputName] and reserve [outputName].
     * Uses MediaStore on API 29+ when direct filesystem write is blocked.
     */
    fun stageInputAndReserveOutput(
        context: Context,
        source: Uri,
        inputName: String,
        outputName: String,
    ): StagedPaths {
        val work = publicWorkDir()
        val inputFile = File(work, inputName)
        val outputFile = File(work, outputName)

        context.contentResolver.openInputStream(source)?.use { input ->
            if (Build.VERSION.SDK_INT >= 29) {
                // Prefer direct write into public Downloads when possible (shared with Termux).
                try {
                    FileOutputStream(inputFile).use { out -> input.copyTo(out) }
                } catch (_: Exception) {
                    val values = ContentValues().apply {
                        put(MediaStore.Downloads.DISPLAY_NAME, inputName)
                        put(MediaStore.Downloads.MIME_TYPE, "application/octet-stream")
                        put(MediaStore.Downloads.RELATIVE_PATH, RELATIVE_DIR)
                        put(MediaStore.Downloads.IS_PENDING, 1)
                    }
                    val collection = MediaStore.Downloads.getContentUri(MediaStore.VOLUME_EXTERNAL_PRIMARY)
                    val dest = context.contentResolver.insert(collection, values)
                        ?: throw IllegalStateException("MediaStore insert failed for $inputName")
                    context.contentResolver.openOutputStream(dest)?.use { out -> input.copyTo(out) }
                        ?: throw IllegalStateException("Cannot open MediaStore output for $inputName")
                    values.clear()
                    values.put(MediaStore.Downloads.IS_PENDING, 0)
                    context.contentResolver.update(dest, values, null, null)
                }
            } else {
                FileOutputStream(inputFile).use { out -> input.copyTo(out) }
            }
        } ?: throw IllegalStateException("Cannot open selected media")

        // Ensure parent exists for Termux output path even if MediaStore was used for input.
        if (!work.exists()) {
            work.mkdirs()
        }
        return StagedPaths(
            inputAbsPath = absoluteUnderDownloads(inputName),
            outputAbsPath = outputFile.absolutePath,
            workDir = work.absolutePath,
        )
    }

    fun displayNameOf(context: Context, uri: Uri, fallback: String = "input.bin"): String {
        context.contentResolver.query(uri, arrayOf(android.provider.OpenableColumns.DISPLAY_NAME), null, null, null)
            ?.use { c ->
                if (c.moveToFirst()) {
                    val idx = c.getColumnIndex(android.provider.OpenableColumns.DISPLAY_NAME)
                    if (idx >= 0) {
                        val name = c.getString(idx)
                        if (!name.isNullOrBlank()) return name
                    }
                }
            }
        return fallback
    }
}
