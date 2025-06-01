import { takeLatest, put, call, select } from 'redux-saga/effects';
import { logger } from '../../utils/logger';
import { getTraceId } from '../../utils/trace';
import { 
  addMessage, 
  updateMessageStatus, 
  markRoomAsRead,
  setConnectionStatus
} from '../slices/chatSlice';
import { 
  connect as connectMQTT, 
  disconnected as mqttDisconnected,
  error as mqttError
} from '../slices/mqttSlice';
import { RootState } from '../store';
import { Message, MessageStatus, RoomType } from '../../types/message';
import { generateMessageId, generateTraceId } from '../../types/message';
import { createAction } from '@reduxjs/toolkit';
import { MQTT_CONFIG } from '../../types/mqtt';

// Action types
export const disconnect = createAction('chat/disconnect');
export const sendMessage = createAction<{ roomId: string; content: string; roomType: RoomType }>('chat/sendMessage');
export const markAsRead = createAction<{ roomId: string; currentUserId: string }>('chat/markAsRead');
export const initializeMqtt = createAction<{ token: string; userId: string }>('chat/initializeMqtt');
export const enterRoom = createAction<{ roomId: string }>('chat/enterRoom');

// Selectors
const getCurrentUserId = (state: RootState) => state.auth.user?.id;

function* handleInitializeMqtt(action: ReturnType<typeof initializeMqtt>): Generator<any, void, any> {
  const { token, userId } = action.payload;
  const traceId = getTraceId();
  
  try {
    logger.info('Dispatching MQTT connect action', { userId, traceId }, 'chat');
    yield put(connectMQTT({ token, userId }));
    logger.info('MQTT connection initiated', { userId, traceId }, 'chat');
  } catch (error) {
    logger.error('Failed to connect to MQTT', { error, traceId }, 'chat');
    yield put(mqttError(error as Error));
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

function* handleSendMessage(action: ReturnType<typeof sendMessage>): Generator<any, void, any> {
  const { roomId, content, roomType } = action.payload;
  const traceId = getTraceId();
  const currentUserId = yield select(getCurrentUserId);

  if (!currentUserId) {
    logger.error('Cannot send message: No current user ID', { traceId }, 'chat');
    return;
  }

  const messageId = generateMessageId();
  const message: Message = {
    id: messageId,
    content,
    sender_id: currentUserId,
    room_id: roomId,
    room_type: roomType,
    status: 'sending',
    timestamp: new Date().toISOString(),
    client_timestamp: new Date().toISOString(),
    trace_id: generateTraceId(messageId)
  };

  try {
    logger.info('Sending message', { messageId: message.id, roomId, traceId }, 'chat');
    yield put(addMessage({ roomId, message }));
    // TODO: Implement actual message sending logic
    yield put(updateMessageStatus({ messageId: message.id, status: 'sent' }));
  } catch (error) {
    logger.error('Failed to send message', { error, traceId }, 'chat');
    yield put(updateMessageStatus({ messageId: message.id, status: 'failed' }));
  }
}

function* handleMarkAsRead(action: ReturnType<typeof markAsRead>): Generator<any, void, any> {
  const { roomId, currentUserId } = action.payload;
  const traceId = getTraceId();

  logger.info('Marking room as read', { roomId, currentUserId, traceId }, 'chat');
  yield put(markRoomAsRead({ roomId, currentUserId }));
}

export function* chatSaga(): Generator<any, void, any> {
  logger.info('Initializing chat sagas', null, 'chat');
  yield takeLatest(initializeMqtt.type, handleInitializeMqtt);
  yield takeLatest(enterRoom.type, handleEnterRoom);
  yield takeLatest(sendMessage.type, handleSendMessage);
  yield takeLatest(markAsRead.type, handleMarkAsRead);
} 