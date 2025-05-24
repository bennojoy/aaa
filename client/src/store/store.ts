import { configureStore } from '@reduxjs/toolkit';
import createSagaMiddleware from 'redux-saga';
import { all } from 'redux-saga/effects';
import { persistStore, persistReducer } from 'redux-persist';
import storage from 'redux-persist/lib/storage';
import authReducer from './authSlice';
import roomReducer from './roomSlice';
import chatReducer from './chatSlice';
import mqttReducer from './mqttSlice';
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
  whitelist: ['user', 'token']
};

const chatPersistConfig = {
  key: 'chat',
  storage,
  whitelist: ['messages'],
  transforms: [
    createTransform(
      // transform state on its way to being serialized and persisted
      (inboundState: any) => {
        return inboundState;
      },
      // transform state being rehydrated
      (outboundState: any) => {
        return outboundState;
      },
      // define which reducers this transform gets called for
      { whitelist: ['messages'] }
    )
  ]
};

const mqttPersistConfig = {
  key: 'mqtt',
  storage,
  whitelist: ['currentUserId', 'currentToken']
};

// Create persisted reducers
const persistedAuthReducer = persistReducer(authPersistConfig, authReducer);
const persistedChatReducer = persistReducer(chatPersistConfig, chatReducer);
const persistedMqttReducer = persistReducer(mqttPersistConfig, mqttReducer);

// Create store
export const store = configureStore({
  reducer: {
    auth: persistedAuthReducer,
    rooms: roomReducer,
    chat: persistedChatReducer,
    mqtt: persistedMqttReducer
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        ignoredActions: [FLUSH, REHYDRATE, PAUSE, PERSIST, PURGE, REGISTER]
      }
    }).concat(sagaMiddleware, mqttMiddleware),
  devTools: process.env.NODE_ENV !== 'production'
});

// Create persistor
export const persistor = persistStore(store, null, () => {
  logger.info('State rehydration complete', { traceId: getTraceId() }, 'store');
});

// Run saga middleware
sagaMiddleware.run(rootSaga);

// Export types
export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch; 