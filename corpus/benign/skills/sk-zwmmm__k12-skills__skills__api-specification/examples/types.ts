export interface GlobalHowItem {
  id: number;
  name: string;
  groupId: number;
  language: string;
  productId: number;
  sort: number;
  createdByName: string;
  createdDate: string;
  lastModifiedByName: string;
  lastModifiedDate: string;
  deletable?: number;
  disable?: number; // 0:关闭 1:开启
  description?: string;
}
