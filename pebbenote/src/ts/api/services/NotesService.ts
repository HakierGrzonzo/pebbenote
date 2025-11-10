/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { NoteEditModel } from "../models/NoteEditModel";
import type { NoteModel } from "../models/NoteModel";
import type { NoteViewModel } from "../models/NoteViewModel";
import type { CancelablePromise } from "../core/CancelablePromise";
import type { BaseHttpRequest } from "../core/BaseHttpRequest";
export class NotesService {
  constructor(public readonly httpRequest: BaseHttpRequest) {}
  /**
   * List Notes
   * @param xPebbleUserToken
   * @returns NoteModel Successful Response
   * @throws ApiError
   */
  public listNotes(
    xPebbleUserToken: string,
  ): CancelablePromise<Array<NoteModel>> {
    return this.httpRequest.request({
      method: "GET",
      url: "/note/",
      headers: {
        "X-pebble-user-token": xPebbleUserToken,
      },
      errors: {
        422: `Validation Error`,
      },
    });
  }
  /**
   * Create Note
   * @param content
   * @param xPebbleUserToken
   * @returns NoteModel Successful Response
   * @throws ApiError
   */
  public createNote(
    content: string,
    xPebbleUserToken: string,
  ): CancelablePromise<NoteModel> {
    return this.httpRequest.request({
      method: "POST",
      url: "/note/",
      headers: {
        "X-pebble-user-token": xPebbleUserToken,
      },
      query: {
        content: content,
      },
      errors: {
        422: `Validation Error`,
      },
    });
  }
  /**
   * Get Note By Id
   * @param noteId
   * @param xPebbleUserToken
   * @returns NoteViewModel Successful Response
   * @throws ApiError
   */
  public getNoteById(
    noteId: string,
    xPebbleUserToken: string,
  ): CancelablePromise<NoteViewModel> {
    return this.httpRequest.request({
      method: "GET",
      url: "/note/{note_id}",
      path: {
        note_id: noteId,
      },
      headers: {
        "X-pebble-user-token": xPebbleUserToken,
      },
      errors: {
        422: `Validation Error`,
      },
    });
  }
  /**
   * Edit Note By Id
   * @param noteId
   * @param xPebbleUserToken
   * @param requestBody
   * @returns NoteModel Successful Response
   * @throws ApiError
   */
  public editNoteById(
    noteId: string,
    xPebbleUserToken: string,
    requestBody: NoteEditModel,
  ): CancelablePromise<NoteModel> {
    return this.httpRequest.request({
      method: "PATCH",
      url: "/note/{note_id}",
      path: {
        note_id: noteId,
      },
      headers: {
        "X-pebble-user-token": xPebbleUserToken,
      },
      body: requestBody,
      mediaType: "application/json",
      errors: {
        422: `Validation Error`,
      },
    });
  }
}
