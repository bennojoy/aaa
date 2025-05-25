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
} from '../roomSlice';
import { logger } from '../../utils/logger';
import { getTraceId } from '../../utils/trace';
import { AxiosResponse } from 'axios';
import { RoomList, CreateRoomParams, AddParticipantParams } from '../../types/room';

/**
 * Handle room search request
 * Fetches rooms from the API based on search parameters
 * 
 * @param action - The search request action containing search parameters
 * @yields {object} - API response containing room list
 * @throws {Error} - If the API request fails
 */
function* handleSearchRooms(action: ReturnType<typeof searchRoomsRequest>): Generator<any, void, AxiosResponse<any>> {
  const { query, skip = 0, limit = 100 } = action.payload;
  const traceId = getTraceId();

  logger.info('Starting room search', { query, skip, limit, traceId }, 'room');

  try {
    const response = yield call(apiClient.get, '/api/v1/rooms/search', {
      params: { query, skip, limit }
    });

    // Transform the response to match the expected structure
    const transformedData: RoomList = {
      items: response.data.rooms || [],
      total: response.data.total || 0,
      skip: skip,
      limit: limit
    };

    logger.info('Room search successful', {
      count: transformedData.items.length,
      query,
      traceId: response.data.trace_id
    }, 'room');

    yield put(searchRoomsSuccess(transformedData));
  } catch (error: any) {
    logger.error('Room search failed', {
      error: error.message,
      query,
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

  logger.info('Creating new room', { name, type, traceId }, 'room');

  try {
    const response = yield call(apiClient.post, '/api/v1/rooms', {
      name,
      description,
      type
    });

    logger.info('Room created successfully', {
      roomId: response.data.id,
      name,
      traceId: response.data.trace_id
    }, 'room');

    yield put(createRoomSuccess(response.data));
  } catch (error: any) {
    logger.error('Room creation failed', {
      error: error.message,
      name,
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
  const { roomId, userId, role = 'member', status = 'active' } = action.payload;
  const traceId = getTraceId();

  logger.info('Adding participant to room', { roomId, userId, role, traceId }, 'room');

  try {
    const response = yield call(apiClient.post, `/api/v1/rooms/${roomId}/participants`, {
      user_id: userId,
      role,
      status
    });

    logger.info('Participant added successfully', {
      roomId,
      userId,
      traceId: response.data.trace_id
    }, 'room');

    yield put(addParticipantSuccess());
  } catch (error: any) {
    logger.error('Failed to add participant', {
      error: error.message,
      roomId,
      userId,
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