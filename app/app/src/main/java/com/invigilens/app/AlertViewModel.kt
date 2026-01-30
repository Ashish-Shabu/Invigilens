package com.invigilens.app

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

data class AlertUiState(
    val alerts: List<AlertDto> = emptyList(),
    val loading: Boolean = false,
    val error: String? = null,
    val online: Boolean = false,
    val socketConnected: Boolean = false,
    val selectedAlert: AlertDto? = null,
    val detailLoading: Boolean = false
)

class AlertViewModel(
    private val repository: AlertRepository,
    private val socketManager: SocketManager
) : ViewModel() {

    private val _state = MutableStateFlow(AlertUiState())
    val state: StateFlow<AlertUiState> = _state

    private var healthJob: Job? = null

    init {
        refreshAlerts()
        startHealthChecks()
        socketManager.connect()
        observeSocket()
    }

    private fun observeSocket() {
        viewModelScope.launch {
            socketManager.newAlerts.collect {
                refreshAlerts()
            }
        }
        viewModelScope.launch {
            while (true) {
                _state.value = _state.value.copy(socketConnected = socketManager.isConnected())
                delay(2000)
            }
        }
    }

    fun refreshAlerts() {
        viewModelScope.launch {
            _state.value = _state.value.copy(loading = true, error = null)
            try {
                val alerts = repository.listAlerts(limit = 50, offset = 0, status = null)
                _state.value = _state.value.copy(alerts = alerts, loading = false)
            } catch (e: Exception) {
                _state.value = _state.value.copy(loading = false, error = e.message)
            }
        }
    }

    fun updateStatus(id: String, status: String) {
        viewModelScope.launch {
            try {
                repository.updateStatus(id, status)
                refreshAlerts()
                // If the updated alert is the one currently selected, refresh it too
                if (_state.value.selectedAlert?.id == id) {
                    selectAlert(id)
                }
            } catch (e: Exception) {
                _state.value = _state.value.copy(error = e.message)
            }
        }
    }

    fun selectAlert(id: String?) {
        if (id == null) {
            _state.value = _state.value.copy(selectedAlert = null, detailLoading = false)
            return
        }
        viewModelScope.launch {
            _state.value = _state.value.copy(detailLoading = true, error = null)
            try {
                val alert = repository.getAlert(id)
                _state.value = _state.value.copy(selectedAlert = alert, detailLoading = false)
            } catch (e: Exception) {
                _state.value = _state.value.copy(detailLoading = false, error = e.message)
            }
        }
    }

    private fun startHealthChecks() {
        healthJob?.cancel()
        healthJob = viewModelScope.launch {
            while (true) {
                val ok = repository.health()
                _state.value = _state.value.copy(online = ok)
                delay(10_000)
            }
        }
    }

    override fun onCleared() {
        socketManager.disconnect()
        healthJob?.cancel()
        super.onCleared()
    }
}
