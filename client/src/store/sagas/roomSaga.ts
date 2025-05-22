import { call, put, takeLatest } from 'redux-saga/effects';
import { apiClient } from '../../api/client';
import { searchRoomsRequest, searchRoomsSuccess, searchRoomsFailure } from '../roomSlice';
import { logger } from '../../utils/logger';
import { getTraceId } from '../../utils/trace';
import { AxiosResponse } from 'axios';
import { RoomList } from '../../types/room';

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
 * Watch for room-related actions and trigger appropriate sagas
 * Initializes the room saga watchers
 */
export function* roomSaga() {
  logger.info('Initializing room sagas', null, 'room');
  yield takeLatest(searchRoomsRequest.type, handleSearchRooms);
} 