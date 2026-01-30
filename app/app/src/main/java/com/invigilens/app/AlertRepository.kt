package com.invigilens.app

class AlertRepository(private val api: ApiService) {
    suspend fun listAlerts(limit: Int = 50, offset: Int = 0, status: String? = null): List<AlertDto> =
        api.getAlerts(limit, offset, status)

    suspend fun getAlert(id: String): AlertDto = api.getAlert(id)

    suspend fun updateStatus(id: String, status: String): AlertDto =
        api.updateStatus(id, UpdateStatusRequest(status))

    suspend fun health(): Boolean = try {
        api.health().status.equals("ok", ignoreCase = true)
    } catch (_: Exception) {
        false
    }
}
