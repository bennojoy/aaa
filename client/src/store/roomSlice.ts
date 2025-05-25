import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { Room, RoomList, RoomSearchParams, CreateRoomParams, AddParticipantParams } from '../types/room';
import { logger } from '../utils/logger';

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
  addingParticipant: false,
};

const roomSlice = createSlice({
  name: 'room',
  initialState,
  reducers: {
    searchRoomsRequest: (state, action: PayloadAction<RoomSearchParams>) => {
      state.loading = true;
      state.error = null;
    },
    searchRoomsSuccess: (state, action: PayloadAction<RoomList>) => {
      state.loading = false;
      // Deduplicate rooms by ID before setting them in state
      const uniqueRooms = action.payload.items.reduce((acc: Room[], room) => {
        if (!acc.find(r => r.id === room.id)) {
          acc.push(room);
        }
        return acc;
      }, []);
      
      logger.info('Setting rooms in state', {
        totalRooms: uniqueRooms.length,
        originalCount: action.payload.items.length,
        removedDuplicates: action.payload.items.length - uniqueRooms.length
      }, 'room');
      
      state.rooms = uniqueRooms;
      state.total = uniqueRooms.length;
    },
    searchRoomsFailure: (state, action: PayloadAction<string>) => {
      state.loading = false;
      state.error = action.payload;
    },
    createRoomRequest: (state, action: PayloadAction<CreateRoomParams>) => {
      state.creatingRoom = true;
      state.error = null;
    },
    createRoomSuccess: (state, action: PayloadAction<Room>) => {
      state.creatingRoom = false;
      // Check if room already exists before adding
      const roomExists = state.rooms.some(room => room.id === action.payload.id);
      
      if (!roomExists) {
        logger.info('Adding new room to state', {
          roomId: action.payload.id,
          roomName: action.payload.name
        }, 'room');
        state.rooms.unshift(action.payload);
        state.total += 1;
      } else {
        logger.info('Room already exists in state, skipping add', {
          roomId: action.payload.id,
          roomName: action.payload.name
        }, 'room');
      }
    },
    createRoomFailure: (state, action: PayloadAction<string>) => {
      state.creatingRoom = false;
      state.error = action.payload;
    },
    addParticipantRequest: (state, action: PayloadAction<AddParticipantParams>) => {
      state.addingParticipant = true;
      state.error = null;
    },
    addParticipantSuccess: (state) => {
      state.addingParticipant = false;
    },
    addParticipantFailure: (state, action: PayloadAction<string>) => {
      state.addingParticipant = false;
      state.error = action.payload;
    },
    clearRoomError: (state) => {
      state.error = null;
    },
  },
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
  clearRoomError,
} = roomSlice.actions;

export default roomSlice.reducer; 