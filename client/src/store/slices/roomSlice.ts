import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { Room, RoomList, RoomSearchParams, CreateRoomParams, AddParticipantParams } from '../../types/room';
import { logger } from '../../utils/logger';
import { getTraceId } from '../../utils/trace';

interface RoomState {
  rooms: Room[];
  total: number;
  loading: boolean;
  error: string | null;
  creatingRoom: boolean;
  addingParticipant: boolean;
}

const initialState: RoomState = {
  rooms: [],
  total: 0,
  loading: false,
  error: null,
  creatingRoom: false,
  addingParticipant: false
};

const roomSlice = createSlice({
  name: 'rooms',
  initialState,
  reducers: {
    searchRoomsRequest: (state, action: PayloadAction<RoomSearchParams>) => {
      logger.info('Search rooms request', { 
        query: action.payload.query,
        traceId: getTraceId() 
      }, 'rooms');
      state.loading = true;
      state.error = null;
    },
    searchRoomsSuccess: (state, action: PayloadAction<RoomList>) => {
      logger.info('Search rooms success', { 
        count: action.payload.rooms.length,
        total: action.payload.total,
        traceId: getTraceId() 
      }, 'rooms');
      state.rooms = action.payload.rooms;
      state.total = action.payload.total;
      state.loading = false;
      state.error = null;
    },
    searchRoomsFailure: (state, action: PayloadAction<string>) => {
      logger.error('Search rooms failure', { 
        error: action.payload,
        traceId: getTraceId() 
      }, 'rooms');
      state.loading = false;
      state.error = action.payload;
    },
    createRoomRequest: (state, action: PayloadAction<CreateRoomParams>) => {
      logger.info('Create room request', { 
        name: action.payload.name,
        type: action.payload.type,
        traceId: getTraceId() 
      }, 'rooms');
      state.creatingRoom = true;
      state.error = null;
    },
    createRoomSuccess: (state, action: PayloadAction<Room>) => {
      logger.info('Create room success', { 
        roomId: action.payload.id,
        traceId: getTraceId() 
      }, 'rooms');
      state.rooms.push(action.payload);
      state.total += 1;
      state.creatingRoom = false;
      state.error = null;
    },
    createRoomFailure: (state, action: PayloadAction<string>) => {
      logger.error('Create room failure', { 
        error: action.payload,
        traceId: getTraceId() 
      }, 'rooms');
      state.creatingRoom = false;
      state.error = action.payload;
    },
    addParticipantRequest: (state, action: PayloadAction<AddParticipantParams>) => {
      logger.info('Add participant request', { 
        roomId: action.payload.roomId,
        userId: action.payload.userId,
        traceId: getTraceId() 
      }, 'rooms');
      state.addingParticipant = true;
      state.error = null;
    },
    addParticipantSuccess: (state, action: PayloadAction<{ roomId: string; participant: { id: string; name: string; role: 'member' | 'admin'; status: 'active' | 'inactive' } }>) => {
      logger.info('Add participant success', { 
        roomId: action.payload.roomId,
        participantId: action.payload.participant.id,
        traceId: getTraceId() 
      }, 'rooms');
      const room = state.rooms.find(r => r.id === action.payload.roomId);
      if (room) {
        if (!room.participants) {
          room.participants = [];
        }
        room.participants.push(action.payload.participant);
      }
      state.addingParticipant = false;
      state.error = null;
    },
    addParticipantFailure: (state, action: PayloadAction<string>) => {
      logger.error('Add participant failure', { 
        error: action.payload,
        traceId: getTraceId() 
      }, 'rooms');
      state.addingParticipant = false;
      state.error = action.payload;
    },
    clearRoomError: (state) => {
      state.error = null;
    }
  }
});

export const {
  searchRoomsRequest,
  searchRoomsSuccess,
  searchRoomsFailure,
  createRoomRequest,
  createRoomSuccess,
  createRoomFailure,
  addParticipantRequest,
  addParticipantSuccess,
  addParticipantFailure,
  clearRoomError
} = roomSlice.actions;

const reducer = roomSlice.reducer;
console.log('Room reducer exported:', {
  reducer: !!reducer,
  actions: {
    searchRoomsRequest: !!searchRoomsRequest,
    searchRoomsSuccess: !!searchRoomsSuccess,
    searchRoomsFailure: !!searchRoomsFailure
  },
  initialState: { ...initialState }
});

export default reducer; 