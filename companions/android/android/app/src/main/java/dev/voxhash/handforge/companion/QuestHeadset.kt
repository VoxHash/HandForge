package dev.voxhash.handforge.companion

import android.os.Build

/**
 * Meta Quest headsets run Android / Horizon OS. The HandForge companion APK
 * (same WebView + LocalEncode stack as phones) is the supported on-headset
 * encode path — there is no separate Quest-native FFmpeg binary.
 */
object QuestHeadset {

    /** True when running on a Meta / Oculus Quest-class device. */
    fun isQuestDevice(
        manufacturer: String = Build.MANUFACTURER,
        brand: String = Build.BRAND,
        model: String = Build.MODEL,
        device: String = Build.DEVICE,
        product: String = Build.PRODUCT,
        hardware: String = Build.HARDWARE,
    ): Boolean {
        val blob = listOf(manufacturer, brand, model, device, product, hardware)
            .joinToString(" ")
            .lowercase()
        return blob.contains("oculus") || blob.contains("quest")
    }
}
