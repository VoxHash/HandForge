package dev.voxhash.handforge.companion

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class QuestHeadsetTest {

    @Test
    fun detectsOculusQuest() {
        assertTrue(
            QuestHeadset.isQuestDevice(
                manufacturer = "Oculus",
                brand = "oculus",
                model = "Quest 3",
                device = "eureka",
                product = "eureka",
                hardware = "qcom",
            ),
        )
    }

    @Test
    fun detectsMetaQuestModel() {
        assertTrue(
            QuestHeadset.isQuestDevice(
                manufacturer = "Meta",
                brand = "meta",
                model = "Quest 3S",
                device = "quest3s",
                product = "quest3s",
                hardware = "qcom",
            ),
        )
    }

    @Test
    fun rejectsOrdinaryPhone() {
        assertFalse(
            QuestHeadset.isQuestDevice(
                manufacturer = "Google",
                brand = "google",
                model = "Pixel 8",
                device = "shiba",
                product = "shiba",
                hardware = "tensor",
            ),
        )
    }
}
