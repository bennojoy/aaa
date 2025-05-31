import { call, put, takeLatest } from 'redux-saga/effects';
import { apiClient } from '../../api/client';
import { 
  searchRoomsRequest, 
  searchRoomsSuccess, 
  searchRoomsFailure,
  createRoomRequest,
  createRoomSuccess,
  createRoomFailure,
  addParticipantRequest,
  addParticipantSuccess,
  addParticipantFailure
} from '../slices/roomSlice';
import { logger } from '../../utils/logger';
import { getTraceId } from '../../utils/trace';
import { AxiosResponse } from 'axios';
import { Room, RoomList } from '../../types/room';

type RoomParticipant = {
  id: string;
  name: string;
  role: 'member' | 'admin';
  status: 'active' | 'inactive';
};

/**
 * Handle room search request
 * Fetches rooms from the API based on search parameters
 * 
 * @param action - The search request action containing search parameters
 * @yields {object} - API response containing room list
 * @throws {Error} - If the API request fails
 */
function* handleSearchRooms(action: ReturnType<typeof searchRoomsRequest>): Generator<any, void, AxiosResponse<any>> {
  const { query } = action.payload;
  const traceId = getTraceId();

  try {
    logger.info('Searching rooms', { query, traceId }, 'room');
    const response = yield call(apiClient.get, '/api/v1/rooms', {
      params: { query }
    });

    console.log('API Response:', {
      data: response.data,
      rooms: response.data.rooms,
      total: response.data.total
    });

    // Transform response to match RoomList type
    const roomList: RoomList = {
      rooms: response.data.rooms || [],  // Use rooms array from response
      total: response.data.total || 0,
      trace_id: traceId
    };

    console.log('Transformed RoomList:', {
      rooms: roomList.rooms,
      total: roomList.total,
      trace_id: roomList.trace_id
    });

    logger.info('Rooms search successful', {
      total: roomList.total,
      count: roomList.rooms.length,
      traceId
    }, 'room');

    // Create the action
    const successAction = searchRoomsSuccess(roomList);
    console.log('Created success action:', successAction);

    // Dispatch the action
    yield put(successAction);

    // Log after dispatch
    console.log('Saga: Action dispatched, waiting for reducer');
  } catch (error: any) {
    logger.error('Rooms search failed', {
      error: error.message,
      status: error.response?.status,
      traceId
    }, 'room');

    yield put(searchRoomsFailure(error.response?.data?.detail || 'Failed to search rooms'));
  }
}

/**
 * Handle room creation request
 * Creates a new room with the specified parameters
 */
function* handleCreateRoom(action: ReturnType<typeof createRoomRequest>): Generator<any, void, AxiosResponse<any>> {
  const { name, description, type } = action.payload;
  const traceId = getTraceId();

  try {
    logger.info('Creating room', { name, type, traceId }, 'room');
    const response = yield call(apiClient.post, '/api/v1/rooms', {
      name,
      description,
      type
    });

    logger.info('Room created successfully', { 
      roomId: response.data.id,
      traceId 
    }, 'room');

    yield put(createRoomSuccess(response.data as Room));
  } catch (error: any) {
    logger.error('Room creation failed', {
      error: error.message,
      status: error.response?.status,
      traceId
    }, 'room');

    yield put(createRoomFailure(error.response?.data?.detail || 'Failed to create room'));
  }
}

/**
 * Handle add participant request
 * Adds a user to a room with the specified role
 */
function* handleAddParticipant(action: ReturnType<typeof addParticipantRequest>): Generator<any, void, AxiosResponse<any>> {
  const { roomId, userId } = action.payload;
  const traceId = getTraceId();

  try {
    logger.info('Adding participant to room', { roomId, userId, traceId }, 'room');
    const response = yield call(apiClient.post, `/api/v1/rooms/${roomId}/participants`, {
      user_id: userId
    });

    logger.info('Participant added successfully', { 
      roomId,
      userId,
      traceId 
    }, 'room');

    const participant: RoomParticipant = {
      id: response.data.id,
      name: response.data.name,
      role: response.data.role || 'member',
      status: response.data.status || 'active'
    };

    yield put(addParticipantSuccess({
      roomId,
      participant
    }));
  } catch (error: any) {
    logger.error('Failed to add participant', {
      error: error.message,
      status: error.response?.status,
      traceId
    }, 'room');

    yield put(addParticipantFailure(error.response?.data?.detail || 'Failed to add participant'));
  }
}

/**
 * Watch for room-related actions and trigger appropriate sagas
 * Initializes the room saga watchers
 */
export function* roomSaga() {
  logger.info('Initializing room sagas', null, 'room');
  yield takeLatest(searchRoomsRequest.type, handleSearchRooms);
  yield takeLatest(createRoomRequest.type, handleCreateRoom);
  yield takeLatest(addParticipantRequest.type, handleAddParticipant);
} 