/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ActionEditModel } from "../models/ActionEditModel";
import type { NoteModel } from "../models/NoteModel";
import type { CancelablePromise } from "../core/CancelablePromise";
import type { BaseHttpRequest } from "../core/BaseHttpRequest";
export class ActionsService {
  constructor(public readonly httpRequest: BaseHttpRequest) {}
  /**
   * Apply Action
   * @param xPebbleUserToken
   * @param requestBody
   * @returns NoteModel Successful Response
   * @throws ApiError
   */
  public applyAction(
    xPebbleUserToken: string,
    requestBody: ActionEditModel,
  ): CancelablePromise<NoteModel> {
    return this.httpRequest.request({
      method: "POST",
      url: "/action/",
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
