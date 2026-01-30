package com.invigilens.app

import com.squareup.moshi.Json
import com.squareup.moshi.JsonClass

@JsonClass(generateAdapter = true)
data class AlertDto(
    @Json(name = "_id") val id: String,
    val studentId: String = "",
    val violationType: String = "",
    val confidence: Double = 0.0,
    val timestamp: String = "",
    val status: String = "pending",
    val evidencePath: String? = null
)

@JsonClass(generateAdapter = true)
data class HealthResponse(
    val status: String = ""
)

@JsonClass(generateAdapter = true)
data class UpdateStatusRequest(
    val status: String
)
