package com.invigilens.app

import io.socket.client.IO
import io.socket.client.Socket
import kotlinx.coroutines.channels.BufferOverflow
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.SharedFlow

class SocketManager(private val baseUrl: String = "http://10.0.2.2:5000") {

    private var socket: Socket? = null

    private val _newAlerts = MutableSharedFlow<Unit>(extraBufferCapacity = 1, onBufferOverflow = BufferOverflow.DROP_OLDEST)
    val newAlerts: SharedFlow<Unit> = _newAlerts

    fun connect() {
        if (socket != null) return
        socket = IO.socket(baseUrl)
        socket?.on(Socket.EVENT_CONNECT) {
            // No-op: connection indicator handled separately
        }
        socket?.on("new_alert") {
            _newAlerts.tryEmit(Unit)
        }
        socket?.connect()
    }

    fun isConnected(): Boolean = socket?.connected() == true

    fun disconnect() {
        socket?.disconnect()
        socket = null
    }
}
