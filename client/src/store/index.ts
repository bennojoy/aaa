import { configureStore } from '@reduxjs/toolkit';
import createSagaMiddleware from 'redux-saga';
import { all } from 'redux-saga/effects';
import authReducer from './authSlice';
import roomReducer from './roomSlice';
import { authSaga } from './sagas/authSaga';
import { roomSaga } from './sagas/roomSaga';

// Create saga middleware
const sagaMiddleware = createSagaMiddleware();

// Create root saga
function* rootSaga() {
  yield all([
    authSaga(),
    roomSaga(),
  ]);
}

// Configure store
export const store = configureStore({
  reducer: {
    auth: authReducer,
    room: roomReducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware().concat(sagaMiddleware),
});

// Run saga middleware
sagaMiddleware.run(rootSaga);

// Export types
export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch; 