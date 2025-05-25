import { call, put, takeLatest, select } from 'redux-saga/effects';
import { connect, setUserId } from '../mqttSlice';
import { 
  addMessage, 
  updateMessageStatus, 
  markRoomAsRead
} from '../chatSlice';
import { generateMessageId, generateTraceId, Message, MessageStatus, RoomType } from '../../types/message';
import { logger } from '../../utils/logger';
import { getTraceId } from '../../utils/trace';
import { createAction } from '@reduxjs/toolkit';
import { MQTT_CONFIG } from '../../config/mqtt';
import { RootState } from '../../store';

// Action types
const SEND_MESSAGE = 'chat/sendMessage';
const INITIALIZE_MQTT = 'chat/initializeMqtt';
const ENTER_ROOM = 'chat/enterRoom';
const MARK_MESSAGES_AS_READ = 'chat/markMessagesAsRead';

// Action creators
export const sendMessage = createAction<{ roomId: string; content: string; roomType: string; messageId: string }>('chat/sendMessage');
export const markMessagesAsRead = createAction<{ roomId: string; currentUserId: string }>('chat/markMessagesAsRead');
export const initializeMqtt = createAction<{ token: string; userId: string }>('chat/initializeMqtt');
export const enterRoom = createAction<{ roomId: string }>('chat/enterRoom');

// Selectors
const getCurrentUserId = (state: any) => state.auth.user?.id;

function* handleInitializeMqtt(action: ReturnType<typeof initializeMqtt>): Generator<any, void, any> {
  const { token, userId } = action.payload;
  const traceId = getTraceId();

  logger.info('Initializing MQTT connection', { 
    userId, 
    hasToken: !!token,
    traceId,
    config: MQTT_CONFIG
  }, 'chat');

  try {
    // First set the user ID in the MQTT state
    yield put(setUserId(userId));
    
    // Then dispatch connect action which will be handled by middleware
    logger.info('Dispatching MQTT connect action', { userId, traceId }, 'chat');
    yield put(connect({ token, userId }));
    logger.info('MQTT connection initiated', { userId, traceId }, 'chat');
  } catch (error) {
    logger.error('Failed to initialize MQTT', { 
      error,
      userId,
      traceId,
      config: MQTT_CONFIG
    }, 'chat');
  }
}

function* handleEnterRoom(action: ReturnType<typeof enterRoom>): Generator<any, void, any> {
  const { roomId } = action.payload;
  const traceId = getTraceId();
  const currentUserId = yield select((state: RootState) => state.mqtt.currentUserId);

  logger.info('Entering room', { roomId, traceId }, 'chat');
  // Mark messages as read when entering room
  yield put(markRoomAsRead({ roomId, currentUserId }));
}

export function* chatSaga(): Generator<any, void, any> {
  yield takeLatest(INITIALIZE_MQTT, handleInitializeMqtt);
  yield takeLatest(ENTER_ROOM, handleEnterRoom);
} 