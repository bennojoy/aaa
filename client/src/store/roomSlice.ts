import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { Room, RoomList, RoomSearchParams, CreateRoomParams, AddParticipantParams } from '../types/room';

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
      state.rooms = action.payload.items;
      state.total = action.payload.total;
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
      state.rooms.unshift(action.payload);
      state.total += 1;
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