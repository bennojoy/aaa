import { configureStore } from '@reduxjs/toolkit';
import createSagaMiddleware from 'redux-saga';
import { all } from 'redux-saga/effects';
import authReducer from './authSlice';
import roomReducer from './roomSlice';
import chatReducer from './chatSlice';
import mqttReducer from './mqttSlice';
import { authSaga } from './sagas/authSaga';
import { roomSaga } from './sagas/roomSaga';
import { chatSaga } from './sagas/chatSaga';
import { mqttMiddleware } from './middleware/mqttMiddleware';

// Create saga middleware
const sagaMiddleware = createSagaMiddleware();

// Create root saga
function* rootSaga() {
  yield all([
    authSaga(),
    roomSaga(),
    chatSaga()
  ]);
}

// Configure store
export const store = configureStore({
  reducer: {
    auth: authReducer,
    room: roomReducer,
    chat: chatReducer,
    mqtt: mqttReducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware().concat(sagaMiddleware, mqttMiddleware),
});

// Make store accessible to MQTT message handler
if (typeof window !== 'undefined') {
  (window as any).__REDUX_STORE__ = store;
}

// Run saga middleware
sagaMiddleware.run(rootSaga);

// Export types
export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch; 