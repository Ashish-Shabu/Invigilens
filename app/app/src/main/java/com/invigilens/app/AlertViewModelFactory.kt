package com.invigilens.app

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider

class AlertViewModelFactory(private val baseUrl: String = "http://10.0.2.2:5000/") : ViewModelProvider.Factory {
    override fun <T : ViewModel> create(modelClass: Class<T>): T {
        if (modelClass.isAssignableFrom(AlertViewModel::class.java)) {
            val api = NetworkModule.apiService(baseUrl)
            val repo = AlertRepository(api)
            val socket = SocketManager(baseUrl.removeSuffix("/"))
            @Suppress("UNCHECKED_CAST")
            return AlertViewModel(repo, socket) as T
        }
        throw IllegalArgumentException("Unknown ViewModel class")
    }
}
