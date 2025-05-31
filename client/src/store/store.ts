import { configureStore } from '@reduxjs/toolkit';
import createSagaMiddleware from 'redux-saga';
import { all } from 'redux-saga/effects';
import { persistStore, persistReducer } from 'redux-persist';
import storage from 'redux-persist/lib/storage';
import authReducer from './slices/authSlice';
import roomReducer from './slices/roomSlice';
import chatReducer from './slices/chatSlice';
import mqttReducer from './slices/mqttSlice';
import { authSaga } from './sagas/authSaga';
import { roomSaga } from './sagas/roomSaga';
import { chatSaga } from './sagas/chatSaga';
import { mqttMiddleware } from './middleware/mqttMiddleware';
import { logger } from '../utils/logger';
import { getTraceId } from '../utils/trace';
import { createTransform } from 'redux-persist';
import { FLUSH, REHYDRATE, PAUSE, PERSIST, PURGE, REGISTER } from 'redux-persist';

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

// Create persist configs
const authPersistConfig = {
  key: 'auth',
  storage,
  whitelist: ['user', 'token', 'isAuthenticated']
};

const roomPersistConfig = {
  key: 'rooms',
  storage,
  whitelist: ['rooms', 'total'],
  transforms: [
    createTransform(
      // transform state on its way to being serialized and persisted
      (inboundState: any) => {
        console.log('Persisting room state:', inboundState);
        return {
          rooms: inboundState.rooms || [],
          total: inboundState.total || 0
        };
      },
      // transform state being rehydrated
      (outboundState: any) => {
        console.log('Rehydrating room state:', outboundState);
        return {
          rooms: outboundState?.rooms || [],
          total: outboundState?.total || 0,
          loading: false,
          error: null,
          creatingRoom: false,
          addingParticipant: false
        };
      }
    )
  ]
};

const chatPersistConfig = {
  key: 'chat',
  storage,
  whitelist: ['messages']
};

const mqttPersistConfig = {
  key: 'mqtt',
  storage,
  whitelist: ['currentUserId', 'currentToken']
};

// Create persisted reducers
const persistedAuthReducer = persistReducer(authPersistConfig, authReducer);
const persistedRoomReducer = persistReducer(roomPersistConfig, roomReducer);
const persistedChatReducer = persistReducer(chatPersistConfig, chatReducer);
const persistedMqttReducer = persistReducer(mqttPersistConfig, mqttReducer);

// Log reducer registration
console.log('Reducers registered:', {
  auth: !!persistedAuthReducer,
  rooms: !!persistedRoomReducer,
  chat: !!persistedChatReducer,
  mqtt: !!persistedMqttReducer
});

// Create store
export const store = configureStore({
  reducer: {
    auth: persistedAuthReducer,
    rooms: persistedRoomReducer, // Use persisted reducer
    chat: persistedChatReducer,
    mqtt: persistedMqttReducer
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        ignoredActions: [FLUSH, REHYDRATE, PAUSE, PERSIST, PURGE, REGISTER]
      },
      immutableCheck: false
    }).concat(sagaMiddleware, mqttMiddleware),
  devTools: true
});

// Create persistor
export const persistor = persistStore(store);

// Log initial state
console.log('Initial store state:', store.getState());

// Add store subscription for debugging
store.subscribe(() => {
  const currentState = store.getState();
  console.log('Store state updated:', {
    rooms: currentState.rooms,
    action: currentState.rooms?.rooms,
    total: currentState.rooms?.total
  });
});

// Run saga middleware
sagaMiddleware.run(rootSaga);

// Export types
export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch; 