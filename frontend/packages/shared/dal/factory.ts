import type { IChatClient, IMaterialClient, ICampaignClient, IMonitorClient, IAuthClient } from './interfaces'
import { MockChatClient, MockMaterialClient, MockCampaignClient, MockMonitorClient, MockAuthClient } from './mock-client'
import { HttpChatClient, HttpMaterialClient, HttpCampaignClient, HttpMonitorClient, HttpAuthClient } from './http-client'

export interface DALClients {
  chat: IChatClient
  material: IMaterialClient
  campaign: ICampaignClient
  monitor: IMonitorClient
  auth: IAuthClient
}

let _clients: DALClients | null = null

export function createDAL(demoMode: boolean, apiBaseUrl: string): DALClients {
  if (_clients) return _clients

  if (demoMode) {
    _clients = {
      chat: new MockChatClient(),
      material: new MockMaterialClient(),
      campaign: new MockCampaignClient(),
      monitor: new MockMonitorClient(),
      auth: new MockAuthClient(),
    }
  } else {
    _clients = {
      chat: new HttpChatClient(apiBaseUrl),
      material: new HttpMaterialClient(apiBaseUrl),
      campaign: new HttpCampaignClient(apiBaseUrl),
      monitor: new HttpMonitorClient(apiBaseUrl),
      auth: new HttpAuthClient(apiBaseUrl),
    }
  }

  return _clients
}

export function getDAL(): DALClients {
  if (!_clients) {
    throw new Error('DAL 未初始化，请先调用 createDAL()')
  }
  return _clients
}
