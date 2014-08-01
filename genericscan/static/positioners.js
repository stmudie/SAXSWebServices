var positionerStruct = {
    SampleTableX: 'SR13ID01HU02IOC01:SMPL_TBL_X_MTR',
    SampleTableY: 'SR13ID01HU02IOC02:SMPL_TBL_Y_MTR',
    GSAXS_X: 'SR13ID01HU02IOC01:SYR_PMP_1_MTR',
    GSAXS_Y: 'SR13ID01HU02IOC01:SYR_PMP_2_MTR',
    Omega: 'SR13ID01HU02IOC01:GSAX_OMG_MTR',
    Phi: 'SR13ID01HU02IOC01:SMPL_PHI_MTR',
    Energy: 'SR13ID01HU01:ENERGY_REQ',
    FileNumber: '13PIL1:cam1:FileNumber',
    WAXS2Theta: 'SR13ID01HU02IOC01:WAX_TTH_MTR',
    Newport_Rot: 'SR13ID01HU02IOC01:SPARE_3_MTR',
    Chi: 'SR13ID01HU02IOC01:GSAX_CHI_MTR',
    Chi_Speed: 'SR13ID01HU02IOC01:GSAX_CHI_MTR.VELO',
    None: ''
}
var detectorStruct = {
    'WAXSROI1': '13PIL2:Stats1:Total_RBV',
    'WAXSROI2': '13PIL2:Stats2:Total_RBV',
    'WAXSROI3': '13PIL2:Stats3:Total_RBV',
    'Scaler4': 'SR13ID01HU02IOC02:scaler1.S4'
}
var detectorTrigStruct = {
    'Pilatus1M': '13PIL1:cam1:Acquire',
    'Scan1': 'SR13ID01HU02IOC02:scan1.EXSC',
    'Scan2': 'SR13ID01HU02IOC02:scan2.EXSC',
    'Scan3': 'SR13ID01HU02IOC02:scan3.EXSC',
    'Scaler': 'SR13ID01HU02IOC02:scaler1.CNT'
    
}
var positionerTestStruct = {
    SampleTableX: 'SMTEST:SMPL_TBL_X_MTR',
    SampleTableY: 'SMTEST:SMPL_TBL_Y_MTR',
    Omega: 'SMTEST:GSAX_OMG_MTR',
    FakeTemperature: '',
    None: ''
}
