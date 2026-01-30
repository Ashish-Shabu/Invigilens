package com.invigilens.app

import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.PUT
import retrofit2.http.Path
import retrofit2.http.Query

interface ApiService {
    @GET("api/alerts")
    suspend fun getAlerts(
        @Query("limit") limit: Int = 50,
        @Query("offset") offset: Int = 0,
        @Query("status") status: String? = null
    ): List<AlertDto>

    @GET("api/alerts/{id}")
    suspend fun getAlert(@Path("id") id: String): AlertDto

    @PUT("api/alerts/{id}")
    suspend fun updateStatus(
        @Path("id") id: String,
        @Body body: UpdateStatusRequest
    ): AlertDto

    @GET("api/health")
    suspend fun health(): HealthResponse
}
